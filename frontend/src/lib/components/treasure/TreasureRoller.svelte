<script>
  import { api } from '$lib/api.js';
  import TreasureRollResult from './TreasureRollResult.svelte';

  export let treasureType = '';
  export let count = 1;
  export let showInput = true;

  let rolling = false;
  let results = [];
  let error = '';

  let inputType = treasureType;
  let inputCount = count;

  async function roll() {
    const tt = showInput ? inputType.trim() : treasureType;
    const ct = showInput ? parseInt(inputCount) || 1 : count;
    if (!tt) { error = 'Enter a treasure type.'; return; }

    rolling = true;
    error = '';
    results = [];
    try {
      results = await api.post('/treasure/roll', {
        treasure_type: tt,
        count: ct,
      });
    } catch (e) {
      error = e.message;
    } finally {
      rolling = false;
    }
  }

  // Auto-roll on mount if treasureType is pre-set and showInput is false
  $: if (!showInput && treasureType) {
    inputType = treasureType;
    inputCount = count;
  }
</script>

<div>
  {#if showInput}
    <div class="flex flex-wrap gap-3 items-end mb-4">
      <div>
        <label class="block text-xs text-ink-faint mb-1" for="tt-input">Treasure Type</label>
        <input id="tt-input" class="input w-32" type="text" bind:value={inputType} placeholder="A" />
      </div>
      <div>
        <label class="block text-xs text-ink-faint mb-1" for="tt-count">Count</label>
        <input id="tt-count" class="input w-20" type="number" min="1" max="100" bind:value={inputCount} />
      </div>
      <button class="btn" on:click={roll} disabled={rolling}>
        {rolling ? 'Rolling...' : 'Roll Treasure'}
      </button>
    </div>
  {:else}
    <button class="btn mb-4" on:click={roll} disabled={rolling}>
      {rolling ? 'Rolling...' : `Roll ${treasureType}`}
    </button>
  {/if}

  {#if error}
    <p class="text-red-700 text-sm mb-3">{error}</p>
  {/if}

  {#if results.length > 0}
    <div class="space-y-3">
      {#each results as result, i}
        <TreasureRollResult {result} index={results.length > 1 ? i : null} />
      {/each}

      <!-- Aggregate summary for multiple rolls -->
      {#if results.length > 1}
        {@const totalCoins = {}}
        {@const _ = results.forEach(r => Object.entries(r.coins).forEach(([k, v]) => totalCoins[k] = (totalCoins[k] || 0) + v))}
        {@const grandTotal = results.reduce((s, r) => s + r.total_gp_value, 0)}
        <div class="panel bg-parchment-100/50 border-ink-faint/50">
          <div class="text-xs text-ink-faint uppercase tracking-wide mb-2">Combined Total ({results.length} rolls)</div>
          <div class="flex flex-wrap gap-4">
            {#each ['pp', 'gp', 'ep', 'sp', 'cp'] as coin}
              {#if (totalCoins[coin] || 0) > 0}
                <div class="text-center">
                  <div class="font-serif text-xl text-ink">{totalCoins[coin].toLocaleString()}</div>
                  <div class="text-xs text-ink-faint">{coin.toUpperCase()}</div>
                </div>
              {/if}
            {/each}
          </div>
          <div class="mt-2 text-right">
            <span class="font-serif text-lg text-ink">{grandTotal.toLocaleString()} gp</span>
            <span class="text-xs text-ink-faint ml-1">combined value</span>
          </div>
        </div>
      {/if}
    </div>
  {/if}
</div>
