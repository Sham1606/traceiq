import { mkdir, readFile, rm, stat, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repositoryRoot = path.resolve(scriptDirectory, '../..');
const outputDirectory = path.join(repositoryRoot, 'demo', 'recordings');
const argumentsSet = new Set(process.argv.slice(2));
const appUrl = new URL(getArgument('--app-url', 'http://127.0.0.1:5173'));
const backendUrl = new URL(getArgument('--backend-url', 'http://127.0.0.1:8001'));
const shouldStartInvestigation = argumentsSet.has('--start-investigation');
const approvalIsExplicit = argumentsSet.has('--approve-synthetic');
const showExistingHighRiskSimulation = argumentsSet.has('--show-existing-high-risk-simulation');
const captureWidth = 1600;
const captureHeight = 900;
const minimumDurationMs = 195_000;
const maximumDurationMs = 240_000;
const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
const recordingTempDirectory = path.join(tmpdir(), 'traceiq-playwright', timestamp);
const videoPath = path.join(outputDirectory, `traceiq-demo-${timestamp}.webm`);
const reportPath = path.join(outputDirectory, `traceiq-demo-${timestamp}.report.json`);
const report = {
  status: 'running',
  started_at: new Date().toISOString(),
  app_url: appUrl.origin,
  backend_url: backendUrl.origin,
  ai_mode: null,
  scenario: null,
  video: null,
  completed_steps: [],
  failure: null,
};

let browser;
let context;
let page;
let video;
let captureStartedAt = 0;
let currentStep = 'preflight';
let failure = null;
const runtimeErrors = [];
const apiRequestFailures = [];

class DemoFailure extends Error {}

function getArgument(name, fallback) {
  const prefix = `${name}=`;
  const inlineValue = process.argv.slice(2).find((value) => value.startsWith(prefix));
  if (inlineValue) return inlineValue.slice(prefix.length);
  const index = process.argv.indexOf(name);
  if (index >= 0 && process.argv[index + 1]) return process.argv[index + 1];
  return fallback;
}

function assertLocalUrl(url, label) {
  const hostname = url.hostname.replace(/^\[|\]$/g, '').toLowerCase();
  if (!['127.0.0.1', 'localhost', '::1'].includes(hostname)) {
    throw new DemoFailure(`${label} must use a loopback address.`);
  }
  if (!['http:', 'https:'].includes(url.protocol)) {
    throw new DemoFailure(`${label} must use HTTP or HTTPS.`);
  }
}

function backendEndpoint(endpoint) {
  return new URL(endpoint.replace(/^\//, ''), `${backendUrl.origin}/`);
}

async function readJson(endpoint, allowNotFound = false) {
  let response;
  try {
    response = await fetch(backendEndpoint(endpoint));
  } catch {
    throw new DemoFailure('The local demo backend could not be reached.');
  }
  if (allowNotFound && response.status === 404) return null;
  if (!response.ok) {
    throw new DemoFailure(`A read-only demo preflight request failed (HTTP ${response.status}).`);
  }
  return response.json();
}

function investigationIsDemoReady(investigation) {
  const telemetry = investigation?.evidence?.ai_telemetry;
  return Boolean(
    investigation?.status === 'complete' &&
    telemetry?.provider === 'mock' &&
    telemetry?.mode === 'mock' &&
    telemetry?.fallback_used !== true &&
    (investigation.evidence?.evidence?.length ?? 0) > 0 &&
    (investigation.evidence?.investigator_findings?.length ?? 0) >= 2 &&
    (investigation.hypotheses?.length ?? 0) >= 2 &&
    investigation.challenge?.status,
  );
}

function isDesignatedSyntheticIncident(incident, requestedId) {
  const isBadDeploymentPayment =
    incident.scenario_id === 'bad-deployment' && /payment/i.test(incident.title);
  const isPaymentProviderScenario =
    incident.scenario_id === 'external-dependency' && /payment/i.test(incident.title);
  const isExplicitMockLabFixture =
    incident.scenario_id === 'LIVE_CUSTOM' &&
    incident.title === 'Order Processing Latency' &&
    requestedId === incident.id;
  return isBadDeploymentPayment || isPaymentProviderScenario || isExplicitMockLabFixture;
}

async function recordStep(name, locator, holdMs = 12_000) {
  currentStep = name;
  await locator.waitFor({ state: 'visible' });
  await locator.scrollIntoViewIfNeeded();
  await page.waitForTimeout(holdMs);
  report.completed_steps.push(name);
  if (runtimeErrors.length || apiRequestFailures.length) {
    throw new DemoFailure('The page reported a runtime or API request failure.');
  }
}

async function waitForEnabled(locator, timeoutMs = 30_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await locator.isEnabled()) return;
    await page.waitForTimeout(250);
  }
  throw new DemoFailure('The expected application control did not become enabled.');
}

async function getActions(investigationId) {
  return readJson(`/api/v1/investigations/${encodeURIComponent(investigationId)}/recovery-actions`);
}

async function getAction(actionId) {
  return readJson(`/api/v1/recovery-actions/${encodeURIComponent(actionId)}`);
}

async function preflight() {
  assertLocalUrl(appUrl, 'App URL');
  assertLocalUrl(backendUrl, 'Backend URL');
  if (appUrl.pathname !== '/' || backendUrl.pathname !== '/') {
    throw new DemoFailure('App and backend URLs must be origin-only URLs.');
  }

  const health = await readJson('/health');
  if (health.status !== 'ok' || health.db !== 'ok') {
    throw new DemoFailure('The local backend or PostgreSQL health check failed.');
  }
  if (health.ai_mode !== 'mock') {
    throw new DemoFailure('The demo backend must report AI mode MOCK; no Gemini request will be made.');
  }
  report.ai_mode = health.ai_mode;

  const incidentList = await readJson('/api/v1/incidents?skip=0&limit=100');
  const incidents = incidentList.items || [];
  const matches = incidents.filter((incident) =>
    incident.scenario_id === 'bad-deployment' && /payment/i.test(incident.title),
  );
  const requestedId = getArgument('--incident-id', null);
  const incident = requestedId
    ? incidents.find((candidate) =>
      candidate.id === requestedId && isDesignatedSyntheticIncident(candidate, requestedId),
    )
    : matches.length === 1
      ? matches[0]
      : null;
  if (!incident) {
    throw new DemoFailure('Could not uniquely identify the local bad-deployment payment scenario.');
  }
  report.scenario = {
    id: incident.id,
    title: incident.title,
    scenario_id: incident.scenario_id,
  };

  const investigations = await readJson(
    `/api/v1/incidents/${encodeURIComponent(incident.id)}/investigations`,
  );
  const existingIds = new Set(investigations.map((investigation) => investigation.id));
  const requestedInvestigationId = getArgument('--investigation-id', null);
  if (shouldStartInvestigation) {
    if (requestedInvestigationId) {
      throw new DemoFailure('Choose either --start-investigation or --investigation-id, not both.');
    }
    if (!approvalIsExplicit) {
      throw new DemoFailure('Pass --approve-synthetic to authorize the local synthetic recovery demonstration.');
    }
    return { incident, existingIds };
  }

  const ready = requestedInvestigationId
    ? investigations.find((investigation) =>
      investigation.id === requestedInvestigationId && investigationIsDemoReady(investigation),
    )
    : investigations.find(investigationIsDemoReady);
  if (!ready) {
    throw new DemoFailure('No matching complete Mock investigation is persisted. Pass --start-investigation with the Mock backend.');
  }
  return { incident, existingIds, ready };
}

async function runRecording() {
  await mkdir(outputDirectory, { recursive: true });
  await mkdir(recordingTempDirectory, { recursive: true });
  const { incident, existingIds, ready } = await preflight();

  browser = await chromium.launch({ headless: false, channel: 'chrome' });
  context = await browser.newContext({
    viewport: { width: captureWidth, height: captureHeight },
    screen: { width: captureWidth, height: captureHeight },
    deviceScaleFactor: 1,
    locale: 'en-US',
    recordVideo: {
      dir: recordingTempDirectory,
      size: { width: captureWidth, height: captureHeight },
    },
  });
  page = await context.newPage();
  page.setDefaultTimeout(30_000);
  captureStartedAt = Date.now();
  video = page.video();

  page.on('pageerror', (error) => runtimeErrors.push(error.name || 'PageError'));
  page.on('requestfailed', (request) => {
    const requestUrl = new URL(request.url());
    if (requestUrl.pathname.startsWith('/api/') || requestUrl.pathname === '/health') {
      apiRequestFailures.push(requestUrl.pathname);
    }
  });

  await page.route(`${appUrl.origin}/**`, async (route) => {
    const requestUrl = new URL(route.request().url());
    if (!requestUrl.pathname.startsWith('/api/') && requestUrl.pathname !== '/health') {
      await route.continue();
      return;
    }
    const upstreamUrl = new URL(`${requestUrl.pathname}${requestUrl.search}`, backendUrl);
    try {
      const upstreamResponse = await route.fetch({ url: upstreamUrl.toString() });
      await route.fulfill({ response: upstreamResponse });
    } catch {
      apiRequestFailures.push(requestUrl.pathname);
      await route.abort('failed');
    }
  });

  currentStep = 'incident dashboard';
  await page.goto(new URL('/incidents', appUrl).toString(), { waitUntil: 'domcontentloaded' });
  await page.getByRole('heading', { name: 'Incident Directory' }).waitFor({ state: 'visible' });
  const search = page.getByPlaceholder('Search by ID, title, service, or scenario...');
  await search.fill(incident.id);
  const incidentRow = page.getByRole('row').filter({ hasText: incident.id });
  await incidentRow.waitFor({ state: 'visible' });
  await recordStep('Incident dashboard and verified scenario selection', incidentRow, 12_000);

  currentStep = 'incident workspace';
  await incidentRow.getByRole('button', { name: 'Investigate', exact: true }).click();
  await page.getByRole('heading', { name: incident.title, exact: true }).waitFor({ state: 'visible' });

  if (shouldStartInvestigation) {
    currentStep = 'Mock investigation';
    const runButton = page.getByRole('button', { name: /^(Start Investigation|Re-run Investigation)$/ }).first();
    await runButton.click();
    await page.getByRole('button', { name: 'Re-run Investigation', exact: true }).waitFor({ state: 'visible', timeout: 180_000 });
    const investigations = await readJson(
      `/api/v1/incidents/${encodeURIComponent(incident.id)}/investigations`,
    );
    const newest = investigations[0];
    if (!newest || existingIds.has(newest.id) || !investigationIsDemoReady(newest)) {
      throw new DemoFailure('The actual Mock investigation did not return the required evidence, findings, competing hypotheses, and Challenge.');
    }
    report.investigation = {
      id: newest.id,
      provider: newest.evidence.ai_telemetry.provider,
      mode: newest.evidence.ai_telemetry.mode,
      evidence_count: newest.evidence.evidence.length,
      investigator_domains: newest.evidence.investigator_findings.map((finding) => finding.domain),
      hypothesis_count: newest.hypotheses.length,
      challenge_status: newest.challenge.status,
    };
  } else {
    report.investigation = {
      id: ready.id,
      provider: ready.evidence.ai_telemetry.provider,
      mode: ready.evidence.ai_telemetry.mode,
      evidence_count: ready.evidence.evidence.length,
      investigator_domains: ready.evidence.investigator_findings.map((finding) => finding.domain),
      hypothesis_count: ready.hypotheses.length,
      challenge_status: ready.challenge.status,
    };
  }

  const investigationId = report.investigation.id;
  await page.getByText('AI MODE MOCK', { exact: true }).waitFor({ state: 'visible' });
  await recordStep(
    'Incident workspace and deterministic evidence synthesis',
    page.getByText('Investigation Executive Summary', { exact: true }),
    12_000,
  );

  await page.getByRole('button', { name: 'Evidence Directory', exact: true }).click();
  await recordStep(
    'Telemetry and evidence directory',
    page.getByRole('heading', { name: 'Metric Telemetry Findings', exact: true }),
    13_000,
  );

  await recordStep(
    'Specialized investigator findings',
    page.getByRole('heading', { name: 'Investigation Progress', exact: true }),
    12_000,
  );

  await page.getByRole('button', { name: 'Correlation Flow', exact: true }).click();
  await recordStep(
    'Cross-signal correlation and causal sequence',
    page.getByRole('heading', { name: 'Cross-Signal Correlation & Causal Flow', exact: true }),
    13_000,
  );

  await page.getByRole('button', { name: 'Competing Hypotheses', exact: true }).click();
  await recordStep(
    'Competing hypotheses and evidence support',
    page.getByRole('heading', { name: /Competing Hypotheses Evaluation/ }),
    14_000,
  );

  await recordStep(
    'Root-cause assessment and leading candidate',
    page.getByText('Root Cause Assessment • Leading Candidate', { exact: true }),
    13_000,
  );

  await page.getByRole('button', { name: 'Challenge RCA', exact: true }).click();
  await recordStep(
    'Adversarial Challenge',
    page.getByRole('heading', { name: 'Adversarial Challenge RCA Protocol', exact: true }),
    13_000,
  );

  currentStep = 'recovery recommendation';
  await page.getByRole('button', { name: 'Recovery Workflow', exact: true }).last().click();
  await page.getByRole('heading', { name: 'Recovery Advisor & Human Approval Gate', exact: true }).waitFor({ state: 'visible' });
  let actions = await getActions(investigationId);
  if (actions.length === 0) {
    await page.getByRole('button', { name: 'Propose Recommended Action', exact: true }).first().click();
    await page.getByText('MANDATORY HUMAN GATE', { exact: true }).waitFor({ state: 'visible' });
    actions = await getActions(investigationId);
  }
  if (!actions.length) throw new DemoFailure('No recovery recommendation was returned by the application.');
  let action = actions[0];
  let blast = action.blast_radius || action.detail?.blast_radius;
  if (!blast?.status) throw new DemoFailure('The recovery recommendation has no displayed blast-radius result.');
  const blastRadiusIsSafe = ['SAFE', 'SAFE_WITH_WARNINGS'].includes(blast.status);
  const highRiskSimulationIsAlreadyComplete =
    showExistingHighRiskSimulation &&
    action.approval_status === 'approved' &&
    action.simulated_result === 'safe' &&
    action.execution_simulation?.status === 'SUCCESS';
  if (!blastRadiusIsSafe && !highRiskSimulationIsAlreadyComplete) {
    throw new DemoFailure('The pre-approval blast-radius result is not safe; approval and simulation were stopped.');
  }
  await recordStep(
    'Recovery recommendation and blast-radius assessment',
    page.getByText('Deterministic Blast-Radius Simulation', { exact: true }),
    13_000,
  );

  let approvalPerformedDuringCapture = false;
  if (action.approval_status === 'pending') {
    if (!approvalIsExplicit || !isDesignatedSyntheticIncident(incident, getArgument('--incident-id', null))) {
      throw new DemoFailure('Pending recovery was not approved: the explicit synthetic-demo guard is required.');
    }
    if (!action.requires_human_approval) {
      throw new DemoFailure('Recovery action does not declare its mandatory human approval requirement.');
    }
    await recordStep(
      'Human approval gate before authorization',
      page.getByText('MANDATORY HUMAN GATE', { exact: true }),
      10_000,
    );
    await page.getByPlaceholder('e.g. SRE-Lead-01').fill('Demo Incident Commander');
    await page.getByRole('button', { name: 'Approve Action', exact: true }).click();
    const executeButton = page.getByRole('button', { name: 'Execute Simulation', exact: true });
    await executeButton.waitFor({ state: 'visible' });
    await page.getByText('Demo Incident Commander', { exact: true }).waitFor({ state: 'visible' });
    await waitForEnabled(executeButton);
    action = await getAction(action.id);
    if (action.approval_status !== 'approved') {
      throw new DemoFailure('The application did not record the explicit demo approval.');
    }
    approvalPerformedDuringCapture = true;
    await recordStep(
      'Human approval recorded by the named demo operator',
      page.getByText('approved', { exact: true }),
      10_000,
    );
  } else if (action.approval_status === 'approved') {
    await recordStep(
      'Human approval gate and recorded operator authorization',
      page.getByText(action.approved_by || 'Operator', { exact: true }),
      10_000,
    );
  } else {
    throw new DemoFailure('Recovery is not pending or approved; the script will not bypass the human gate.');
  }

  if (action.simulated_result === 'not_run') {
    currentStep = 'safe synthetic recovery simulation';
    await page.getByRole('button', { name: 'Execute Simulation', exact: true }).click();
    await page.getByRole('button', { name: 'Simulated (SAFE)', exact: true }).waitFor({ state: 'visible' });
    action = await getAction(action.id);
  }
  if (
    action.simulated_result !== 'safe' ||
    action.execution_simulation?.status !== 'SUCCESS'
  ) {
    throw new DemoFailure('The application did not confirm a successful safe synthetic simulation.');
  }
  report.recovery = {
    approval_status: action.approval_status,
    approved_by: action.approved_by,
    blast_radius_status: blast.status,
    simulated_result: action.simulated_result,
    execution_status: action.execution_simulation.status,
    approval_performed_during_capture: approvalPerformedDuringCapture,
  };
  await recordStep(
    'SAFE synthetic simulation result',
    page.getByText(/Simulated Telemetry Shifts/),
    14_000,
  );

  await page.getByRole('button', { name: 'Postmortem', exact: true }).click();
  let postmortem = await readJson(
    `/api/v1/investigations/${encodeURIComponent(investigationId)}/postmortem`,
    true,
  );
  if (!postmortem) {
    await page.getByRole('button', { name: 'Generate Postmortem', exact: true }).click();
    await page.getByText('AUTOMATED POSTMORTEM DRAFT', { exact: true }).waitFor({ state: 'visible' });
    postmortem = await readJson(
      `/api/v1/investigations/${encodeURIComponent(investigationId)}/postmortem`,
    );
  }
  if (!postmortem.evidence_references?.length) {
    throw new DemoFailure('The generated postmortem has no evidence references.');
  }
  report.postmortem = { title: postmortem.title, evidence_reference_count: postmortem.evidence_references.length };
  await recordStep(
    'Evidence-grounded postmortem',
    page.getByText('AUTOMATED POSTMORTEM DRAFT', { exact: true }),
    14_000,
  );

  currentStep = 'historical memory archive';
  const memorySearch = new URL('/api/v1/memory/search', backendUrl);
  memorySearch.searchParams.set('fingerprint', incident.scenario_id);
  memorySearch.searchParams.set('limit', '10');
  let memoryResults = await readJson(`${memorySearch.pathname}${memorySearch.search}`);
  let archivedMemory = memoryResults.matches?.find((match) => match.memory.incident_id === incident.id);
  const memoryWasArchivedBeforeCapture = Boolean(archivedMemory);
  if (!archivedMemory) {
    await page.getByRole('button', { name: 'Archive to Historical Memory', exact: true }).click();
    await page.getByRole('button', { name: 'Archived to Memory', exact: true }).waitFor({ state: 'visible' });
    memoryResults = await readJson(`${memorySearch.pathname}${memorySearch.search}`);
    archivedMemory = memoryResults.matches?.find((match) => match.memory.incident_id === incident.id);
  }
  if (!archivedMemory) throw new DemoFailure('The archived incident memory was not returned by historical search.');

  await page.getByRole('button', { name: 'Historical Memory', exact: true }).click();
  await page.getByText('Historical Memory Rule', { exact: true }).waitFor({ state: 'visible' });
  const memoryEntry = page.getByText(
    `Memory ID: ${archivedMemory.memory.id} • Historical Incident: ${incident.id}`,
    { exact: true },
  ).first();
  await memoryEntry.waitFor({ state: 'visible' });
  report.memory = {
    id: archivedMemory.memory.id,
    title: archivedMemory.memory.title,
    incident_id: archivedMemory.memory.incident_id,
    archived_before_capture: memoryWasArchivedBeforeCapture,
  };
  await recordStep(
    'Historical incident memory and evidence comparison',
    memoryEntry,
    14_000,
  );

  currentStep = 'final duration pacing';
  const elapsed = Date.now() - captureStartedAt;
  if (elapsed < minimumDurationMs) {
    await page.waitForTimeout(minimumDurationMs - elapsed);
  }
  const durationMs = Date.now() - captureStartedAt;
  if (durationMs > maximumDurationMs) {
    throw new DemoFailure('Capture exceeded the four-minute target window.');
  }
  report.duration_seconds = Number((durationMs / 1000).toFixed(1));
  report.completed_steps.push('Three-to-four-minute duration verified');
}

try {
  await runRecording();
} catch (error) {
  failure = error;
  report.failure = {
    step: currentStep,
    reason: error instanceof DemoFailure ? error.message : 'Automation or application step failed; raw error details were not written to the report.',
  };
} finally {
  if (context) {
    try {
      await context.close();
    } catch {
      report.failure ??= { step: currentStep, reason: 'Browser recording context did not close cleanly.' };
    }
  }

  if (video) {
    try {
      const outputVideoPath = report.failure
        ? videoPath.replace(/\.webm$/, '.partial.webm')
        : videoPath;
      await video.saveAs(outputVideoPath);
      const videoBytes = await readFile(outputVideoPath);
      const videoStat = await stat(outputVideoPath);
      const validWebm =
        videoBytes.length > 10_000 &&
        videoBytes[0] === 0x1a &&
        videoBytes[1] === 0x45 &&
        videoBytes[2] === 0xdf &&
        videoBytes[3] === 0xa3;
      if (!validWebm) {
        report.failure ??= { step: 'video verification', reason: 'The output file is not a valid non-empty WebM recording.' };
      } else {
        report.video = {
          path: path.relative(repositoryRoot, outputVideoPath).replaceAll(path.sep, '/'),
          bytes: videoStat.size,
          container: 'WebM (EBML verified)',
          resolution: `${captureWidth}x${captureHeight}`,
        };
      }
    } catch {
      report.failure ??= { step: 'video finalization', reason: 'Playwright could not finalize the browser recording.' };
    }
  }

  try {
    await rm(recordingTempDirectory, { recursive: true, force: true });
  } catch {
    report.failure ??= { step: 'temporary recording cleanup', reason: 'Playwright temporary video files could not be removed.' };
  }

  if (browser) {
    try {
      await browser.close();
    } catch {
      report.failure ??= { step: currentStep, reason: 'Visible Chrome did not close cleanly.' };
    }
  }

  report.status = report.failure ? 'failed' : 'complete';
  report.finished_at = new Date().toISOString();
  await mkdir(outputDirectory, { recursive: true });
  await writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  console.log(`Demo recording status: ${report.status}`);
  console.log(`Report: ${path.relative(repositoryRoot, reportPath).replaceAll(path.sep, '/')}`);
  if (report.video) console.log(`Video: ${report.video.path} (${report.video.bytes} bytes)`);
  if (report.failure) console.error(`Stopped at ${report.failure.step}: ${report.failure.reason}`);
  if (failure || report.failure) process.exitCode = 1;
}