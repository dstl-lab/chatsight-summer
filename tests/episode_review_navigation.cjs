// Run from the repository root: node tests/episode_review_navigation.cjs
// Invented state and deferred fetch responses; no browser, dependencies, or network.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const html = fs.readFileSync(path.join(__dirname, '../src/eval/episode_review.html'), 'utf8');
const script = html.split('<script>')[1].split('</script>')[0];
const controls = new Map(), pending = [], visited = [], requests = [];
const control = id => {
  if (!controls.has(id)) controls.set(id, {
    disabled: false, classList: {toggle() {}}, focus() {},
  });
  return controls.get(id);
};
const context = vm.createContext({
  document: {getElementById: control}, window: {scrollTo() {}},
  performance: {now: () => 0}, clearTimeout, setTimeout: () => 0, visited,
  fetch: (_, options) => {
    const body = JSON.parse(options.body); requests.push(body);
    return new Promise(resolve => pending.push((status = 200) => resolve({
      ok: status === 200, json: async () => status === 200
        ? {review: {...body, revision: (body.revision || 0) + 1}}
        : {detail: `Save failed (${status})`},
    })));
  },
});
// Load the real state declarations and functions, stopping before event wiring/start().
vm.runInContext(script.slice(0, script.indexOf('\n$("previous").addEventListener')), context);
vm.runInContext(`
  session = {episodes: [{id: 'a'}, {id: 'b'}, {id: 'c'}], reviews: {}};
  answer = {episode_id: 'a', complete: false};
  // Rendering itself is covered in the browser; preserve its navigation state changes.
  render = () => {
    visited.push(index);
    answer = {episode_id: session.episodes[index].id, complete: false};
    dirty = false; hasInteraction = false; version++; updateProgress();
  };
`, context);
const tick = () => new Promise(resolve => setImmediate(resolve));

async function main() {
  await vm.runInContext('save()', context);
  assert.equal(pending.length, 0, 'Untouched episodes must not create saved reviews');
  vm.runInContext('hasInteraction = true', context);
  const cleanSave = vm.runInContext('save()', context);
  await tick();
  assert.equal(pending.length, 0, 'Clean reviews must not be autosaved after earlier interaction');
  await cleanSave;
  vm.runInContext('dirty = true', context);
  const autosave = vm.runInContext('save()', context);
  await tick();
  const firstNext = vm.runInContext('navigate(1)', context);
  assert.equal(control('next').disabled, true);
  pending.shift()(); // The older autosave finishes while Next's save is still queued.
  await tick();
  assert.equal(control('next').disabled, true, 'Autosave must not unlock pending navigation');
  const secondNext = vm.runInContext('navigate(1)', context);
  pending.shift()();
  await tick();
  assert.equal(pending.length, 0, 'Overlapping Next must not queue another navigation save');
  await Promise.all([autosave, firstNext, secondNext]);
  assert.deepEqual(requests.map(body => body.revision), [0, 1], 'Queued saves use the revision returned by the previous save');
  assert.deepEqual(visited, [1], 'Overlapping Next must advance exactly one episode');
  assert.equal(control('next').disabled, false, 'Navigation unlocks after the save finishes');
  assert.equal(control('previous').disabled, false);

  for (const [navigationTiming, status] of [['after-success', 409], ['before-duplicate', 503]]) {
    vm.runInContext(`
      session = {episodes: [{id: 'a'}, {id: 'b'}], reviews: {}};
      index = 0; dirty = true; hasInteraction = true; version++;
      answer = {episode_id: 'a', complete: false, instructor_action: {text: 'A human note'}};
    `, context);
    const first = vm.runInContext(navigationTiming === 'after-success' ? 'save()' : 'navigate(1)', context);
    const duplicate = vm.runInContext('save()', context);
    await tick(); pending.shift()(); await tick();
    const next = navigationTiming === 'after-success' ? vm.runInContext('navigate(1)', context) : first;
    await tick();
    assert.equal(vm.runInContext('index', context), 0, 'Navigation must await every queued save even when the first clears dirty');
    assert.equal(control('next').disabled, true);
    pending.shift()(status);
    await Promise.all([first, duplicate, next]);
    assert.equal(vm.runInContext('answer.episode_id', context), 'a');
    assert.equal(vm.runInContext('answer.instructor_action.text', context), 'A human note');
    assert.equal(vm.runInContext('dirty && hasInteraction', context), true, 'Failed saves remain retryable on their original episode');
    const retry = vm.runInContext('navigate(1)', context);
    await tick(); pending.shift()(); await retry;
    assert.equal(vm.runInContext('index', context), 1);
    assert.equal(vm.runInContext('dirty || hasInteraction', context), false);
  }

  // Development review decisions must be explicit, and must never mutate drafts.
  vm.runInContext(`
    session = {task: 'development', episodes: [{id: 'dev', annotation: {
      request: {value: 'explanation', evidence: [{turn_id: 't1', quote: 'Why?'}], rationale: 'Model reasoning'},
      tutor_response: {value: 'hint', evidence: [{turn_id: 't2', quote: 'Try a loop.'}], rationale: 'Model reasoning'},
      followup: {value: 'substantive-contribution', evidence: [{turn_id: 't3', quote: 'I tried.'}], rationale: 'Model reasoning'}
    }}, {id: 'next'}], reviews: {}};
    index = 0; hasInteraction = false; dirty = false;
    answer = reviewAnswer(currentEpisode());
    showFields = () => {};
  `, context);
  const originalDraft = vm.runInContext('JSON.stringify(currentEpisode().annotation)', context);
  assert.equal(vm.runInContext('Object.keys(answer.judgments).length', context), 0);
  await vm.runInContext('save()', context);
  assert.equal(pending.length, 0, 'Displaying suggestions is not a human review');
  vm.runInContext(`
    chooseAssessment('request', 'accepted');
    chooseAssessment('tutor_response', 'changed');
    answer.judgments.tutor_response.value = 'explanation';
    chooseAssessment('followup', 'cannot-assess');
  `, context);
  assert.equal(vm.runInContext('JSON.stringify(currentEpisode().annotation)', context), originalDraft);
  assert.equal(vm.runInContext('answer.judgments.request.rationale', context), '', 'Do not copy model reasoning as a human note');
  const completion = vm.runInContext('finishReview()', context);
  await tick();
  pending.shift()();
  await completion;
  const saved = JSON.parse(vm.runInContext('JSON.stringify(session.reviews.dev)', context));
  assert.equal(saved.complete, true);
  assert.equal(saved.workflow, 'draft-review');
  assert.equal(saved.judgments.request.assessment, 'accepted');
  assert.equal(saved.judgments.tutor_response.assessment, 'changed');
  assert.equal(saved.judgments.tutor_response.value, 'explanation');
  assert.equal(saved.judgments.followup.assessment, 'cannot-assess');
  assert.equal(saved.judgments.followup.value, null);
  assert.deepEqual(saved.judgments.followup.evidence, []);
  assert.equal(vm.runInContext('index', context), 1);

  vm.runInContext(`
    index = 0; hasInteraction = false; dirty = false;
    answer = reviewAnswer(currentEpisode());
  `, context);
  const acceptAll = vm.runInContext('finishReview()', context);
  await tick();
  pending.shift()();
  await acceptAll;
  const accepted = JSON.parse(vm.runInContext('JSON.stringify(session.reviews.dev)', context));
  assert(Object.values(accepted.judgments).every(j => j.assessment === 'accepted'));

  const legacy = JSON.stringify({episode_id: 'dev', complete: true,
    judgments: {request: {value: 'unclear', evidence: [], rationale: 'Existing human note'}},
    instructor_action: {text: 'Existing action', evidence: []}, elapsed_ms: 123});
  context.legacy = JSON.parse(legacy);
  const restored = JSON.parse(vm.runInContext('JSON.stringify(reviewAnswer(currentEpisode(), legacy))', context));
  assert.equal(restored.judgments.request.value, 'unclear');
  assert.equal(restored.judgments.request.rationale, 'Existing human note');
  assert.equal(restored.workflow, 'manual');
  assert.equal(JSON.stringify(context.legacy), legacy, 'Loading a saved review must not migrate it');
  console.log('Episode navigation and development decisions passed');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
