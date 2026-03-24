<script>
  export let result;
  export let index = null;

  const COIN_ORDER = ['pp', 'gp', 'ep', 'sp', 'cp'];
  const COIN_LABELS = { pp: 'PP', gp: 'GP', ep: 'EP', sp: 'SP', cp: 'CP' };

  $: hasCoins = Object.values(result.coins || {}).some(v => v > 0);
  $: hasGems = (result.gems || []).length > 0;
  $: hasJewelry = (result.jewelry || []).length > 0;
  $: hasMagic = (result.magic_items || []).length > 0;
  $: isEmpty = !hasCoins && !hasGems && !hasJewelry && !hasMagic;

  // Group gems by value for compact display
  $: gemGroups = (() => {
    const groups = {};
    for (const g of result.gems || []) {
      groups[g.value] = (groups[g.value] || 0) + 1;
    }
    return Object.entries(groups).sort((a, b) => b[0] - a[0]);
  })();
</script>

<div class="panel">
  {#if index != null}
    <div class="text-xs text-ink-faint uppercase tracking-wide mb-1">Roll #{index + 1}</div>
  {/if}

  {#if isEmpty}
    <p class="text-ink-faint text-sm italic">Nothing found.</p>
  {:else}
    <div class="space-y-3">
      <!-- Coins -->
      {#if hasCoins}
        <div>
          <div class="text-xs text-ink-faint uppercase tracking-wide mb-1">Coins</div>
          <div class="flex flex-wrap gap-3">
            {#each COIN_ORDER as coin}
              {#if (result.coins[coin] || 0) > 0}
                <div class="text-center">
                  <div class="font-serif text-xl text-ink">{result.coins[coin].toLocaleString()}</div>
                  <div class="text-xs text-ink-faint">{COIN_LABELS[coin]}</div>
                </div>
              {/if}
            {/each}
          </div>
        </div>
      {/if}

      <!-- Gems -->
      {#if hasGems}
        <div>
          <div class="text-xs text-ink-faint uppercase tracking-wide mb-1">
            Gems ({result.gems.length}) — {result.gem_total.toLocaleString()} gp total
          </div>
          <div class="flex flex-wrap gap-2">
            {#each gemGroups as [value, count]}
              <span class="text-xs border border-ink-faint/30 rounded px-2 py-0.5">
                {count} x {parseInt(value).toLocaleString()} gp
              </span>
            {/each}
          </div>
        </div>
      {/if}

      <!-- Jewelry -->
      {#if hasJewelry}
        <div>
          <div class="text-xs text-ink-faint uppercase tracking-wide mb-1">
            Jewelry ({result.jewelry.length}) — {result.jewelry_total.toLocaleString()} gp total
          </div>
          <div class="flex flex-wrap gap-2">
            {#each result.jewelry as j}
              <span class="text-xs border border-ink-faint/30 rounded px-2 py-0.5">
                {j.value.toLocaleString()} gp
              </span>
            {/each}
          </div>
        </div>
      {/if}

      <!-- Magic Items -->
      {#if hasMagic}
        <div>
          <div class="text-xs text-ink-faint uppercase tracking-wide mb-1">
            Magic Items ({result.magic_items.length})
          </div>
          <div class="space-y-1">
            {#each result.magic_items as item}
              <div class="text-sm text-ink font-medium">{item}</div>
            {/each}
          </div>
        </div>
      {/if}
    </div>

    <!-- Total -->
    <div class="mt-3 pt-2 border-t border-ink-faint/20 text-right">
      <span class="text-xs text-ink-faint">Estimated value:</span>
      <span class="font-serif text-lg text-ink ml-1">{result.total_gp_value.toLocaleString()} gp</span>
    </div>
  {/if}
</div>
