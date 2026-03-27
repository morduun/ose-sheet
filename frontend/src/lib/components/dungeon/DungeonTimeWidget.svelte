<script>
  import { onMount } from 'svelte';
  import { createDungeonTracker, TORCH_LIFE, LANTERN_LIFE } from '$lib/dungeon-tracker.js';
  import Modal from '$lib/components/shared/Modal.svelte';

  export let campaignId;
  export let rollDice = null;

  let tracker = null;
  let state = null;
  let status = null;
  let alerts = [];
  let alertTimer = null;
  let showManage = false;
  let turnNote = '';

  // Custom timer form
  let newTimerName = '';
  let newTimerDuration = '';

  onMount(() => {
    tracker = createDungeonTracker(campaignId);
    state = tracker.state;
    refreshStatus();
  });

  function refreshStatus() {
    if (!tracker) return;
    status = tracker.getStatus();
  }

  // Re-read status whenever state changes
  $: if ($state) refreshStatus();

  function advance() {
    if (!tracker) return;
    const events = tracker.advanceTurn(turnNote);
    turnNote = '';
    alerts = events;
    if (alertTimer) clearTimeout(alertTimer);
    alertTimer = setTimeout(() => { alerts = []; alertTimer = null; }, 5000);
  }

  function dismissAlerts() {
    alerts = [];
    if (alertTimer) { clearTimeout(alertTimer); alertTimer = null; }
  }

  function addTimer() {
    const name = newTimerName.trim();
    const dur = parseInt(newTimerDuration);
    if (!name || isNaN(dur) || dur <= 0) return;
    tracker.addCustomTimer(name, dur);
    newTimerName = '';
    newTimerDuration = '';
  }

  async function rollWanderingMonster() {
    if (!rollDice) return;
    await rollDice('1d6', (roll) => {
      const encounter = roll <= 1;
      return {
        display: roll,
        text: encounter ? 'Wandering Monster! (1-in-6)' : `No encounter (${roll} vs 1-in-6)`,
      };
    });
  }

  const alertColors = {
    wandering: 'bg-amber-50 border-amber-400 text-amber-900',
    rest: 'bg-blue-50 border-blue-400 text-blue-900',
    torch_expired: 'bg-orange-50 border-orange-400 text-orange-900',
    lantern_expired: 'bg-orange-50 border-orange-400 text-orange-900',
    timer_expired: 'bg-parchment-100 border-ink-faint text-ink',
    darkness: 'bg-red-50 border-red-400 text-red-900',
    note: 'bg-parchment-100 border-ink-faint/50 text-ink italic',
  };
</script>

{#if status}
  <div class="panel py-2 px-3">
    <div class="flex items-center justify-between gap-3">
      <!-- Turn display -->
      <div class="flex items-center gap-3 text-xs">
        <div class="text-center">
          <div class="text-ink-faint uppercase text-[10px]">Turn</div>
          <div class="font-serif text-lg text-ink leading-none">{status.currentTurn}</div>
        </div>
        {#if status.currentTurn > 0}
          <div class="text-ink-faint">
            Hr {status.hourNumber}, T{status.turnInHour}
          </div>
        {/if}
      </div>

      <!-- Light & resources summary -->
      <div class="flex items-center gap-2 text-xs text-ink-faint">
        {#if status.activeTorches > 0}
          <span title="Active torches">🔥{status.activeTorches}</span>
        {/if}
        {#if status.activeLanterns > 0}
          <span title="Active lanterns">🏮{status.activeLanterns}</span>
        {/if}
        {#if status.totalLightSources === 0 && status.currentTurn > 0}
          <span class="text-red-700 font-medium">No light!</span>
        {/if}
        {#if status.nextExpiry < 999}
          <span title="Turns until next light expires">({status.nextExpiry}t)</span>
        {/if}
        {#if status.rationsRemaining >= 0}
          <span title="Rations remaining">🍖{status.rationsRemaining}</span>
        {/if}
        {#if $state?.customTimers?.length > 0}
          {#each $state.customTimers as timer}
            <span class="text-amber-700" title="{timer.name}: {timer.remaining} turns">{timer.name} {timer.remaining}t</span>
          {/each}
        {/if}
      </div>

      <!-- Note + Buttons -->
      <div class="flex items-center gap-1">
        <input
          class="input text-xs py-0.5 px-2 w-36"
          type="text"
          bind:value={turnNote}
          placeholder="What happened..."
          on:keydown={(e) => e.key === 'Enter' && advance()}
        />
        <button class="btn-ghost text-xs" on:click={() => showManage = true} title="Manage resources">Manage</button>
        <button class="btn text-xs" on:click={advance}>
          {status.currentTurn === 0 ? 'Start' : 'Next Turn'}
        </button>
      </div>
    </div>

    <!-- Alert toasts -->
    {#if alerts.length > 0}
      <!-- svelte-ignore a11y-click-events-have-key-events -->
      <!-- svelte-ignore a11y-no-static-element-interactions -->
      <div class="mt-2 space-y-1" on:click={dismissAlerts}>
        {#each alerts as alert}
          <div class="text-xs px-2 py-1 rounded border flex items-center justify-between gap-2 {alertColors[alert.type] ?? 'bg-parchment-100 border-ink-faint/30 text-ink'}">
            <span>{alert.text}</span>
            {#if alert.type === 'wandering' && rollDice}
              <button
                class="btn text-[10px] px-2 py-0 shrink-0"
                on:click|stopPropagation={rollWanderingMonster}
              >Roll 1d6</button>
            {/if}
          </div>
        {/each}
      </div>
    {/if}
  </div>
{/if}

<!-- Resource Management Modal -->
<Modal bind:open={showManage} title="Dungeon Resources" maxWidth="max-w-lg">
  {#if $state}
    <div class="space-y-4">
      <!-- Torches -->
      <div>
        <div class="flex items-center justify-between mb-1">
          <span class="text-sm font-medium text-ink">Torches</span>
          <button class="btn text-xs" on:click={() => tracker.addTorch()}>+ Light Torch</button>
        </div>
        {#if $state.torches.length === 0}
          <p class="text-xs text-ink-faint">No torches lit.</p>
        {:else}
          <div class="space-y-1">
            {#each $state.torches as torch}
              <div class="flex items-center justify-between text-xs border-b border-parchment-200 pb-1">
                <span class="text-ink">🔥 Torch — {torch.remaining}/{TORCH_LIFE} turns</span>
                <button class="btn-danger text-[10px] px-1.5 py-0" on:click={() => tracker.removeTorch(torch.id)}>X</button>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Lanterns -->
      <div>
        <div class="flex items-center justify-between mb-1">
          <span class="text-sm font-medium text-ink">Lanterns</span>
          <button class="btn text-xs" on:click={() => tracker.addLantern()}>+ Light Lantern</button>
        </div>
        {#if $state.lanterns.length === 0}
          <p class="text-xs text-ink-faint">No lanterns.</p>
        {:else}
          <div class="space-y-1">
            {#each $state.lanterns as lantern}
              <div class="flex items-center justify-between text-xs border-b border-parchment-200 pb-1">
                <span class="text-ink {lantern.out ? 'text-ink-faint line-through' : ''}">
                  🏮 Lantern — {lantern.out ? 'Out of oil' : `${lantern.remaining}/${LANTERN_LIFE} turns`}
                </span>
                <div class="flex gap-1">
                  {#if lantern.out}
                    <button class="btn-ghost text-[10px] px-1.5 py-0" on:click={() => tracker.refillLantern(lantern.id)}>Refill</button>
                  {/if}
                  <button class="btn-danger text-[10px] px-1.5 py-0" on:click={() => tracker.removeLantern(lantern.id)}>X</button>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Rations -->
      <div>
        <div class="flex items-center justify-between mb-1">
          <span class="text-sm font-medium text-ink">Rations</span>
        </div>
        <div class="flex items-center gap-3">
          <div class="flex items-center gap-1">
            <button class="btn-ghost text-xs px-1.5" on:click={() => tracker.adjustRations(-1)}>-</button>
            <span class="text-sm text-ink font-medium w-8 text-center">{$state.rationsTotal}</span>
            <button class="btn-ghost text-xs px-1.5" on:click={() => tracker.adjustRations(1)}>+</button>
            <span class="text-xs text-ink-faint ml-1">total</span>
          </div>
          <div class="text-xs text-ink-faint">
            {$state.rationsTotal - $state.rationsConsumed} remaining
          </div>
          <button class="btn-ghost text-xs" on:click={() => tracker.consumeRation()}>Consume 1</button>
        </div>
      </div>

      <!-- Custom Timers -->
      <div>
        <div class="flex items-center justify-between mb-1">
          <span class="text-sm font-medium text-ink">Custom Timers</span>
        </div>
        {#if $state.customTimers.length > 0}
          <div class="space-y-1 mb-2">
            {#each $state.customTimers as timer}
              <div class="flex items-center justify-between text-xs border-b border-parchment-200 pb-1">
                <span class="text-ink">{timer.name} — {timer.remaining} turns</span>
                <button class="btn-danger text-[10px] px-1.5 py-0" on:click={() => tracker.removeCustomTimer(timer.id)}>X</button>
              </div>
            {/each}
          </div>
        {/if}
        <div class="flex gap-2">
          <input class="input flex-1 text-xs" type="text" bind:value={newTimerName} placeholder="Timer name" />
          <input class="input w-16 text-xs" type="number" min="1" bind:value={newTimerDuration} placeholder="Turns" />
          <button class="btn text-xs" on:click={addTimer}>Add</button>
        </div>
      </div>
    </div>
  {/if}
</Modal>
