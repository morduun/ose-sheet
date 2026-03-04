<script>
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api.js';
  import { token } from '$lib/stores.js';
  import { get } from 'svelte/store';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import DiceOverlay from '$lib/components/shared/DiceOverlay.svelte';

  const campaignId = $page.params.id;

  let campaign = null;
  let loading = true;
  let error = '';
  let userId = null;

  // Dice rolling
  let rollDice = null;

  // --- Dungeon tracker state (independent lets) ---
  let currentTurn = 0;
  let torches = [];
  let lanterns = [];
  let rationsTotal = 0;
  let rationsConsumed = 0;
  let customTimers = [];
  let notes = '';
  let history = [];
  let eventAlerts = [];

  // UI state
  let confirmReset = false;
  let historyOpen = false;
  let turnPage = 0;
  let nextId = 1;

  // Custom timer add form
  let newTimerName = '';
  let newTimerDuration = '';

  const TORCH_LIFE = 6;
  const LANTERN_LIFE = 24;
  const TURNS_PER_HOUR = 6;
  const TURNS_PER_PAGE = 24;

  // --- Derived values ---
  $: turnInHour = currentTurn > 0 ? ((currentTurn - 1) % TURNS_PER_HOUR) + 1 : 0;
  $: hourNumber = currentTurn > 0 ? Math.floor((currentTurn - 1) / TURNS_PER_HOUR) + 1 : 0;
  $: rationsRemaining = rationsTotal - rationsConsumed;
  $: activeTorches = torches.filter(t => t.remaining > 0);
  $: activeLanterns = lanterns.filter(l => l.remaining > 0);
  $: totalLightSources = activeTorches.length + activeLanterns.length;

  // Turn grid
  $: totalPages = currentTurn > 0 ? Math.max(1, Math.ceil(currentTurn / TURNS_PER_PAGE)) : 1;
  $: {
    // Auto-advance page when current turn passes the displayed range
    if (currentTurn > 0) {
      const neededPage = Math.ceil(currentTurn / TURNS_PER_PAGE) - 1;
      if (neededPage > turnPage) turnPage = neededPage;
    }
  }
  $: pageStart = turnPage * TURNS_PER_PAGE + 1;
  $: turnCells = Array.from({ length: TURNS_PER_PAGE }, (_, i) => {
    const turn = pageStart + i;
    const events = history.find(h => h.turn === turn)?.events || [];
    return { turn, events };
  });

  function getUserId() {
    const t = get(token);
    if (!t) return null;
    try {
      const payload = JSON.parse(atob(t.split('.')[1]));
      return payload.sub ? parseInt(payload.sub) : null;
    } catch {
      return null;
    }
  }

  $: isGM = campaign && userId && campaign.gm_id === userId;
  $: if (browser && campaign && !isGM) goto(`/campaigns/${campaignId}`);

  // --- localStorage persistence ---
  const storageKey = `dungeon_tracker_${campaignId}`;

  function loadState() {
    try {
      const raw = localStorage.getItem(storageKey);
      if (!raw) return;
      const s = JSON.parse(raw);
      currentTurn = s.currentTurn ?? 0;
      torches = s.torches ?? [];
      lanterns = s.lanterns ?? [];
      rationsTotal = s.rationsTotal ?? 0;
      rationsConsumed = s.rationsConsumed ?? 0;
      customTimers = s.customTimers ?? [];
      notes = s.notes ?? '';
      history = s.history ?? [];
      nextId = s.nextId ?? 1;
    } catch {
      // defaults are fine
    }
  }

  function saveState() {
    try {
      localStorage.setItem(storageKey, JSON.stringify({
        currentTurn,
        torches,
        lanterns,
        rationsTotal,
        rationsConsumed,
        customTimers,
        notes,
        history,
        nextId,
      }));
    } catch {
      // storage full — silently fail
    }
  }

  // --- Core logic ---

  function advanceTurn() {
    currentTurn += 1;
    const events = [];

    // Decrement all active resources
    torches = torches.map(t => ({ ...t, remaining: t.remaining - 1 }));
    lanterns = lanterns.map(l => ({ ...l, remaining: l.remaining - 1 }));
    customTimers = customTimers.map(t => ({ ...t, remaining: t.remaining - 1 }));

    // Check scheduled events
    if (currentTurn % 2 === 0) {
      events.push({ type: 'wandering', text: 'Wandering Monster Check' });
    }
    if (currentTurn % TURNS_PER_HOUR === 0) {
      events.push({ type: 'rest', text: 'Rest Required' });
    }

    // Check expired torches
    const expiredTorches = torches.filter(t => t.remaining <= 0);
    if (expiredTorches.length > 0) {
      events.push({ type: 'torch_expired', text: `${expiredTorches.length} torch(es) burned out` });
      torches = torches.filter(t => t.remaining > 0);
    }

    // Check expired lanterns — mark out but don't remove (can refill)
    const expiredLanterns = lanterns.filter(l => l.remaining <= 0 && !l.out);
    if (expiredLanterns.length > 0) {
      events.push({ type: 'lantern_expired', text: `${expiredLanterns.length} lantern(s) out of oil` });
      lanterns = lanterns.map(l => l.remaining <= 0 ? { ...l, out: true } : l);
    }

    // Check expired custom timers
    const expiredTimers = customTimers.filter(t => t.remaining <= 0);
    for (const t of expiredTimers) {
      events.push({ type: 'timer_expired', text: `${t.name} expired` });
    }
    customTimers = customTimers.filter(t => t.remaining > 0);

    // Darkness warning
    const activeLights = torches.filter(t => t.remaining > 0).length +
                         lanterns.filter(l => l.remaining > 0).length;
    if (activeLights === 0 && (torches.length > 0 || lanterns.length > 0 || expiredTorches.length > 0 || expiredLanterns.length > 0)) {
      events.push({ type: 'darkness', text: 'No active light sources!' });
    }

    // Push to history
    history = [...history, { turn: currentTurn, events: events.map(e => e.text) }];
    eventAlerts = events;
    saveState();
  }

  function undoTurn() {
    if (currentTurn <= 0) return;

    // Re-increment remaining on all active resources
    torches = torches.map(t => ({ ...t, remaining: t.remaining + 1 }));
    lanterns = lanterns.map(l => {
      if (l.out && l.remaining <= 0) {
        // Was just marked out — restore it
        return { ...l, remaining: 1, out: false };
      }
      return { ...l, remaining: l.remaining + 1 };
    });
    customTimers = customTimers.map(t => ({ ...t, remaining: t.remaining + 1 }));

    currentTurn -= 1;
    // Pop last history entry
    history = history.filter(h => h.turn <= currentTurn);
    eventAlerts = [];
    saveState();
  }

  function resetTracker() {
    currentTurn = 0;
    torches = [];
    lanterns = [];
    rationsTotal = 0;
    rationsConsumed = 0;
    customTimers = [];
    notes = '';
    history = [];
    eventAlerts = [];
    nextId = 1;
    turnPage = 0;
    confirmReset = false;
    saveState();
  }

  // --- Resource management ---

  function lightTorch() {
    torches = [...torches, { id: nextId++, lit_at_turn: currentTurn, remaining: TORCH_LIFE }];
    saveState();
  }

  function addLantern() {
    lanterns = [...lanterns, { id: nextId++, lit_at_turn: currentTurn, remaining: LANTERN_LIFE, out: false }];
    saveState();
  }

  function refillLantern(id) {
    lanterns = lanterns.map(l => l.id === id ? { ...l, remaining: LANTERN_LIFE, out: false } : l);
    saveState();
  }

  function removeLantern(id) {
    lanterns = lanterns.filter(l => l.id !== id);
    saveState();
  }

  function consumeRation() {
    if (rationsRemaining <= 0) return;
    rationsConsumed += 1;
    saveState();
  }

  function adjustRations(delta) {
    rationsTotal = Math.max(0, rationsTotal + delta);
    if (rationsConsumed > rationsTotal) rationsConsumed = rationsTotal;
    saveState();
  }

  function addCustomTimer() {
    const name = newTimerName.trim();
    if (!name) return;
    const dur = parseInt(newTimerDuration);
    if (isNaN(dur) || dur <= 0) return;
    customTimers = [...customTimers, { id: nextId++, name, remaining: dur }];
    newTimerName = '';
    newTimerDuration = '';
    saveState();
  }

  function removeTimer(id) {
    customTimers = customTimers.filter(t => t.id !== id);
    saveState();
  }

  async function rollTimerDuration() {
    if (!rollDice) return;
    const notation = newTimerDuration.trim() || '1d6';
    // Only roll if it looks like dice notation
    if (!/^\d*d\d+/i.test(notation)) return;
    await rollDice(notation, (total) => {
      newTimerDuration = String(total);
      return { display: total, text: `Timer duration: ${total} turns` };
    });
  }

  async function rollWanderingMonster() {
    if (!rollDice) return;
    await rollDice('1d6', (roll) => {
      if (roll === 1) {
        return { display: roll, text: 'Wandering Monster!' };
      }
      return { display: roll, text: 'No encounter' };
    });
  }

  function dismissAlerts() {
    eventAlerts = [];
  }

  function handleNotesInput() {
    saveState();
  }

  // --- Lifecycle ---
  onMount(async () => {
    userId = getUserId();
    loadState();
    try {
      campaign = await api.get(`/campaigns/${campaignId}`);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  // Event badge helpers
  function cellBadges(events) {
    const badges = [];
    for (const e of events) {
      if (e.includes('Wandering')) badges.push({ letter: 'W', cls: 'badge-wandering' });
      if (e.includes('Rest')) badges.push({ letter: 'R', cls: 'badge-rest' });
      if (e.includes('torch')) badges.push({ letter: 'T', cls: 'badge-torch' });
      if (e.includes('lantern')) badges.push({ letter: 'L', cls: 'badge-lantern' });
      if (e.includes('Darkness') || e.includes('light')) badges.push({ letter: 'D', cls: 'badge-darkness' });
    }
    return badges;
  }
</script>

<svelte:head>
  <title>Dungeon Tracker — {campaign?.name ?? 'Campaign'} — OSE Sheet</title>
</svelte:head>

{#if loading}
  <PageWrapper><p class="text-ink-faint">Loading...</p></PageWrapper>
{:else if error}
  <PageWrapper><p class="text-red-700">{error}</p></PageWrapper>
{:else if campaign}
  <DiceOverlay bind:roll={rollDice} />
  <PageWrapper title="Dungeon Tracker" maxWidth="max-w-5xl">
    <!-- Header bar -->
    <div class="flex items-center justify-between mb-4 flex-wrap gap-2">
      <div class="flex items-center gap-2">
        <a href="/campaigns/{campaignId}" class="text-xs text-ink-faint hover:text-ink">&larr; {campaign.name}</a>
        <span class="text-ink-faint text-xs">|</span>
        <a href="/campaigns/{campaignId}/referee" class="text-xs text-ink-faint hover:text-ink">Encounter Tracker</a>
      </div>
    </div>

    <!-- Turn Counter & Controls -->
    <div class="panel mb-4">
      <div class="flex items-center justify-between flex-wrap gap-3">
        <div>
          {#if currentTurn === 0}
            <div class="font-serif text-2xl text-ink-faint">Not started</div>
          {:else}
            <div class="font-serif text-3xl text-ink">
              Turn {currentTurn}
            </div>
            <div class="text-sm text-ink-faint mt-0.5">
              Hour {hourNumber}, Turn {turnInHour} of {TURNS_PER_HOUR}
            </div>
          {/if}
        </div>
        <div class="flex items-center gap-2">
          <button class="btn" on:click={advanceTurn}>
            Advance Turn
          </button>
          <button class="btn-ghost text-xs" on:click={undoTurn} disabled={currentTurn <= 0}>
            Undo
          </button>
          {#if !confirmReset}
            <button class="btn-danger text-xs" on:click={() => confirmReset = true} disabled={currentTurn <= 0}>
              Reset
            </button>
          {:else}
            <span class="text-xs text-red-700">Sure?</span>
            <button class="btn-danger text-xs" on:click={resetTracker}>Yes, Reset</button>
            <button class="btn-ghost text-xs" on:click={() => confirmReset = false}>Cancel</button>
          {/if}
        </div>
      </div>
    </div>

    <!-- Event Alerts -->
    {#if eventAlerts.length > 0}
      <div class="mb-4 space-y-2">
        {#each eventAlerts as alert}
          <div class="alert-panel alert-{alert.type}">
            <div class="flex items-center justify-between">
              <span class="font-medium text-sm">{alert.text}</span>
              {#if alert.type === 'wandering'}
                <button class="btn text-xs ml-3" on:click={rollWanderingMonster}>
                  Roll 1d6
                </button>
              {/if}
            </div>
          </div>
        {/each}
        <button class="btn-ghost text-xs" on:click={dismissAlerts}>Dismiss</button>
      </div>
    {/if}

    <!-- Turn Grid -->
    {#if currentTurn > 0}
      <div class="panel mb-4">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs text-ink-faint uppercase tracking-wide">
            Hours {Math.floor(pageStart / TURNS_PER_HOUR) + 1}–{Math.floor((pageStart + TURNS_PER_PAGE - 1) / TURNS_PER_HOUR) + 1}
          </span>
          <div class="flex items-center gap-1">
            <button
              class="btn-ghost text-xs"
              on:click={() => turnPage = Math.max(0, turnPage - 1)}
              disabled={turnPage <= 0}
            >&larr;</button>
            <span class="text-xs text-ink-faint">Page {turnPage + 1}</span>
            <button
              class="btn-ghost text-xs"
              on:click={() => turnPage += 1}
              disabled={turnPage >= totalPages - 1}
            >&rarr;</button>
          </div>
        </div>
        <div class="turn-grid">
          {#each turnCells as cell}
            {@const isPast = cell.turn < currentTurn}
            {@const isCurrent = cell.turn === currentTurn}
            {@const isFuture = cell.turn > currentTurn}
            {@const badges = cellBadges(cell.events)}
            <div
              class="turn-cell"
              class:turn-past={isPast}
              class:turn-current={isCurrent}
              class:turn-future={isFuture}
            >
              <span class="turn-number">{cell.turn}</span>
              {#if badges.length > 0}
                <div class="turn-badges">
                  {#each badges as b}
                    <span class="event-badge {b.cls}" title={b.letter === 'W' ? 'Wandering Monster Check' : b.letter === 'R' ? 'Rest Required' : b.letter === 'T' ? 'Torch Expired' : b.letter === 'L' ? 'Lantern Expired' : 'Darkness'}>{b.letter}</span>
                  {/each}
                </div>
              {/if}
            </div>
          {/each}
        </div>
        <!-- Hour markers -->
        <div class="flex mt-1">
          {#each Array(4) as _, i}
            <div class="flex-1 text-center text-[10px] text-ink-faint border-t border-parchment-200 pt-0.5">
              Hour {Math.floor(pageStart / TURNS_PER_HOUR) + i + 1}
            </div>
          {/each}
        </div>
      </div>
    {/if}

    <!-- Resource Cards -->
    <div class="grid md:grid-cols-2 gap-4 mb-4">
      <!-- Torches -->
      <div class="panel">
        <div class="flex items-center justify-between mb-2">
          <h3 class="section-title mb-0 border-none text-base">Torches</h3>
          <div class="flex items-center gap-2">
            <span class="text-xs text-ink-faint">{activeTorches.length} active</span>
            <button class="btn text-xs" on:click={lightTorch}>+ Light Torch</button>
          </div>
        </div>
        {#if torches.length === 0}
          <p class="text-xs text-ink-faint">No torches lit</p>
        {:else}
          <div class="space-y-1.5">
            {#each torches as torch (torch.id)}
              <div class="flex items-center gap-2">
                <span class="text-xs text-ink w-20">Torch #{torch.id}</span>
                <div class="flex-1 h-2 bg-parchment-200 rounded-full overflow-hidden">
                  <div
                    class="h-full rounded-full transition-all {torch.remaining <= 1 ? 'bg-red-700' : torch.remaining <= 2 ? 'bg-amber-600' : 'bg-amber-500'}"
                    style="width: {Math.max(0, (torch.remaining / TORCH_LIFE) * 100)}%"
                  ></div>
                </div>
                <span class="text-xs text-ink-faint w-12 text-right">{torch.remaining}/{TORCH_LIFE}</span>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Lanterns -->
      <div class="panel">
        <div class="flex items-center justify-between mb-2">
          <h3 class="section-title mb-0 border-none text-base">Lanterns</h3>
          <div class="flex items-center gap-2">
            <span class="text-xs text-ink-faint">{activeLanterns.length} active</span>
            <button class="btn text-xs" on:click={addLantern}>+ Light Lantern</button>
          </div>
        </div>
        {#if lanterns.length === 0}
          <p class="text-xs text-ink-faint">No lanterns</p>
        {:else}
          <div class="space-y-1.5">
            {#each lanterns as lantern (lantern.id)}
              <div class="flex items-center gap-2">
                <span class="text-xs text-ink w-20 {lantern.out ? 'text-red-700' : ''}">
                  {lantern.out ? 'OUT' : 'Lantern'} #{lantern.id}
                </span>
                <div class="flex-1 h-2 bg-parchment-200 rounded-full overflow-hidden">
                  <div
                    class="h-full rounded-full transition-all {lantern.remaining <= 4 ? 'bg-red-700' : lantern.remaining <= 8 ? 'bg-amber-600' : 'bg-sky-600'}"
                    style="width: {Math.max(0, (lantern.remaining / LANTERN_LIFE) * 100)}%"
                  ></div>
                </div>
                <span class="text-xs text-ink-faint w-12 text-right">{Math.max(0, lantern.remaining)}/{LANTERN_LIFE}</span>
                <button class="btn-ghost text-xs px-1" on:click={() => refillLantern(lantern.id)} title="Refill with oil flask">Refill</button>
                <!-- svelte-ignore a11y-click-events-have-key-events -->
                <!-- svelte-ignore a11y-no-static-element-interactions -->
                <span class="cursor-pointer text-ink-faint hover:text-red-700 text-sm" on:click={() => removeLantern(lantern.id)} title="Remove lantern">&times;</span>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Rations -->
      <div class="panel">
        <div class="flex items-center justify-between mb-2">
          <h3 class="section-title mb-0 border-none text-base">Rations</h3>
        </div>
        <div class="flex items-center gap-4">
          <div class="text-center">
            <div class="font-serif text-3xl {rationsRemaining <= 2 && rationsTotal > 0 ? 'text-red-700' : 'text-ink'}">{rationsRemaining}</div>
            <div class="text-xs text-ink-faint">remaining</div>
          </div>
          <div class="flex flex-col gap-1">
            <div class="flex items-center gap-1">
              <span class="text-xs text-ink-faint w-12">Supply:</span>
              <button class="btn-ghost text-xs px-1.5" on:click={() => adjustRations(-1)} disabled={rationsTotal <= 0}>-</button>
              <span class="text-sm font-mono w-6 text-center">{rationsTotal}</span>
              <button class="btn-ghost text-xs px-1.5" on:click={() => adjustRations(1)}>+</button>
            </div>
            <button
              class="btn text-xs"
              on:click={consumeRation}
              disabled={rationsRemaining <= 0}
            >Consume Ration</button>
          </div>
        </div>
        {#if rationsRemaining <= 2 && rationsTotal > 0}
          <p class="text-xs text-red-700 mt-2">Low on rations!</p>
        {/if}
        {#if rationsRemaining <= 0 && rationsTotal > 0}
          <p class="text-xs text-red-700 font-bold">No rations remaining!</p>
        {/if}
      </div>

      <!-- Custom Timers -->
      <div class="panel">
        <div class="flex items-center justify-between mb-2">
          <h3 class="section-title mb-0 border-none text-base">Custom Timers</h3>
        </div>
        {#if customTimers.length > 0}
          <div class="space-y-1.5 mb-3">
            {#each customTimers as timer (timer.id)}
              <div class="flex items-center gap-2">
                <span class="text-xs text-ink flex-1 truncate">{timer.name}</span>
                <div class="w-20 h-2 bg-parchment-200 rounded-full overflow-hidden">
                  <div
                    class="h-full rounded-full bg-violet-600 transition-all"
                    style="width: {timer.remaining > 0 ? Math.min(100, (timer.remaining / (timer.remaining + (currentTurn - (timer.id || 0)))) * 100) : 0}%"
                  ></div>
                </div>
                <span class="text-xs text-ink-faint w-10 text-right">{timer.remaining}t</span>
                <!-- svelte-ignore a11y-click-events-have-key-events -->
                <!-- svelte-ignore a11y-no-static-element-interactions -->
                <span class="cursor-pointer text-ink-faint hover:text-red-700 text-sm" on:click={() => removeTimer(timer.id)} title="Remove timer">&times;</span>
              </div>
            {/each}
          </div>
        {:else}
          <p class="text-xs text-ink-faint mb-3">No active timers</p>
        {/if}
        <div class="flex gap-1">
          <input
            class="input flex-1 text-xs"
            type="text"
            bind:value={newTimerName}
            placeholder="Timer name"
          />
          <input
            class="input w-16 text-xs text-center"
            type="text"
            bind:value={newTimerDuration}
            placeholder="turns"
          />
          <button
            class="btn-ghost text-xs px-1.5"
            on:click={rollTimerDuration}
            disabled={!rollDice}
            title="Roll dice for duration"
          >d</button>
          <button class="btn text-xs" on:click={addCustomTimer}>Add</button>
        </div>
      </div>
    </div>

    <!-- Notes -->
    <div class="panel mb-4">
      <h3 class="section-title mb-2 border-none text-base">Notes</h3>
      <textarea
        class="input w-full h-24 text-sm"
        bind:value={notes}
        on:input={handleNotesInput}
        placeholder="Session notes..."
      ></textarea>
    </div>

    <!-- History Log -->
    <div class="panel">
      <button
        class="flex items-center gap-2 w-full text-left"
        on:click={() => historyOpen = !historyOpen}
      >
        <h3 class="section-title mb-0 border-none text-base">Turn History</h3>
        <span class="text-xs text-ink-faint">{historyOpen ? '▾' : '▸'}</span>
        <span class="text-xs text-ink-faint">({history.length} turns)</span>
      </button>
      {#if historyOpen}
        <div class="mt-2 max-h-60 overflow-y-auto">
          {#if history.length === 0}
            <p class="text-xs text-ink-faint">No turns recorded yet.</p>
          {:else}
            {#each [...history].reverse() as entry}
              <div class="text-xs text-ink-faint py-0.5 border-b border-parchment-100 last:border-none">
                <span class="font-medium text-ink">Turn {entry.turn}:</span>
                {#if entry.events.length > 0}
                  {entry.events.join(', ')}
                {:else}
                  No events
                {/if}
              </div>
            {/each}
          {/if}
        </div>
      {/if}
    </div>

    <!-- Undo note -->
    {#if currentTurn > 0}
      <p class="text-[10px] text-ink-faint mt-2 text-center">
        Undo restores active resource counts but does not restore expired items.
      </p>
    {/if}
  </PageWrapper>
{/if}

<style>
  .turn-grid {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 2px;
  }

  .turn-cell {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 0.35rem 0.15rem;
    border: 1px solid var(--parchment-200, #e8dcc8);
    border-radius: 0.25rem;
    min-height: 2.5rem;
  }

  .turn-number {
    font-size: 0.7rem;
    font-weight: 600;
    line-height: 1;
  }

  .turn-past {
    background-color: var(--parchment-200, #e8dcc8);
    opacity: 0.7;
  }

  .turn-current {
    background-color: rgba(180, 140, 60, 0.15);
    border-color: rgb(180, 140, 60);
    border-width: 2px;
    box-shadow: 0 0 4px rgba(180, 140, 60, 0.3);
  }

  .turn-current .turn-number {
    color: rgb(120, 90, 20);
    font-weight: 700;
  }

  .turn-future {
    opacity: 0.35;
  }

  .turn-badges {
    display: flex;
    gap: 1px;
    margin-top: 2px;
  }

  .event-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 0.9rem;
    height: 0.9rem;
    font-size: 0.5rem;
    font-weight: 700;
    line-height: 1;
    border-radius: 50%;
    color: white;
  }

  .badge-wandering {
    background-color: rgb(180, 140, 40);
  }

  .badge-rest {
    background-color: rgb(185, 28, 28);
  }

  .badge-torch {
    background-color: rgb(234, 138, 30);
  }

  .badge-lantern {
    background-color: rgb(14, 116, 144);
  }

  .badge-darkness {
    background-color: rgb(30, 30, 30);
  }

  /* Alert panels */
  .alert-panel {
    padding: 0.5rem 0.75rem;
    border-radius: 0.375rem;
    border-left: 3px solid;
  }

  .alert-wandering {
    background-color: rgba(180, 140, 40, 0.12);
    border-left-color: rgb(180, 140, 40);
    color: rgb(120, 90, 10);
  }

  .alert-rest {
    background-color: rgba(185, 28, 28, 0.08);
    border-left-color: rgb(185, 28, 28);
    color: rgb(153, 27, 27);
  }

  .alert-torch_expired,
  .alert-lantern_expired,
  .alert-timer_expired {
    background-color: rgba(107, 92, 74, 0.08);
    border-left-color: rgba(107, 92, 74, 0.4);
    color: var(--ink-faint, #6b5c4a);
  }

  .alert-darkness {
    background-color: rgba(30, 30, 30, 0.1);
    border-left-color: rgb(153, 27, 27);
    color: rgb(153, 27, 27);
    font-weight: 700;
  }
</style>
