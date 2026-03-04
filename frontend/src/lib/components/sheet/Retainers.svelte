<script>
  import { api } from '$lib/api.js';

  export let character;
  export let isGM = false;
  export let isOwner = false;
  export let rollDice = null;

  let dismissing = null;

  $: retainers = character?.retainers ?? [];
  $: maxRetainers = character?.modifiers?.charisma?.max_retainers ?? 4;
  $: baseLoyalty = character?.modifiers?.charisma?.retainer_loyalty ?? 7;
  $: canHire = (isOwner || isGM) && retainers.length < maxRetainers;

  function hpPct(current, max) {
    return max > 0 ? Math.round((current / max) * 100) : 0;
  }

  function hpColorClass(current, max) {
    const pct = hpPct(current, max);
    if (pct <= 25) return 'text-red-800 font-bold';
    if (pct <= 50) return 'text-amber-700';
    return 'text-green-800';
  }

  async function rollLoyaltyCheck(retainer) {
    if (!rollDice || retainer.loyalty == null) return;
    await rollDice('2d6', (roll) => {
      const result = roll <= retainer.loyalty ? 'Holds!' : 'Leaves!';
      return `${retainer.name} Loyalty ${retainer.loyalty} \u2192 ${result}`;
    });
  }

  async function dismissRetainer(retainer) {
    if (!confirm(`Dismiss ${retainer.name}? They will become an independent character.`)) return;
    dismissing = retainer.id;
    try {
      await api.post(`/characters/${retainer.id}/dismiss`);
      character.retainers = character.retainers.filter(r => r.id !== retainer.id);
      character = character;
    } catch (e) {
      alert(e.message || 'Failed to dismiss retainer');
    } finally {
      dismissing = null;
    }
  }
</script>

<div>
  <!-- Header -->
  <div class="flex items-center justify-between mb-4">
    <h2 class="section-title">
      Retainers ({retainers.length} / {maxRetainers})
    </h2>
    {#if canHire}
      <a
        href="/campaigns/{character.campaign_id}/characters/new?master_id={character.id}"
        class="btn text-sm"
      >
        + Hire Retainer
      </a>
    {/if}
  </div>

  {#if retainers.length === 0}
    <div class="panel text-center py-6">
      <p class="text-ink-faint text-sm">
        No retainers hired. Max: {maxRetainers} (CHA {character.charisma})
      </p>
      <p class="text-ink-faint text-xs mt-1">
        Base loyalty: {baseLoyalty}
      </p>
    </div>
  {:else}
    <div class="grid gap-3 sm:grid-cols-2">
      {#each retainers as retainer (retainer.id)}
        {@const pct = hpPct(retainer.hp_current, retainer.hp_max)}
        <div class="panel">
          <!-- Name + Class -->
          <div class="flex items-start justify-between mb-2">
            <div>
              <a href="/characters/{retainer.id}" class="font-medium text-ink hover:underline">
                {retainer.name}
              </a>
              <div class="text-xs text-ink-faint">
                {retainer.character_class_name ?? 'Unknown'} {retainer.level}
              </div>
            </div>
            <div class="text-right text-xs">
              <div class="text-ink-faint">AC</div>
              <div class="font-serif text-lg text-ink leading-none">{retainer.ac}</div>
            </div>
          </div>

          <!-- HP Bar -->
          <div class="mb-2">
            <div class="flex items-center justify-between text-xs mb-0.5">
              <span class="text-ink-faint">HP</span>
              <span class={hpColorClass(retainer.hp_current, retainer.hp_max)}>
                {retainer.hp_current}/{retainer.hp_max}
              </span>
            </div>
            <div class="h-1.5 bg-parchment-200 rounded-full overflow-hidden">
              <div
                class="h-full rounded-full transition-all {pct <= 25 ? 'bg-red-800' : pct <= 50 ? 'bg-amber-600' : 'bg-green-800'}"
                style="width: {pct}%"
              ></div>
            </div>
          </div>

          <!-- Loyalty + Actions -->
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              {#if retainer.loyalty != null}
                <button
                  class="text-xs px-2 py-0.5 rounded border border-ink-faint/30 hover:bg-parchment-200 transition-colors"
                  disabled={!rollDice}
                  on:click={() => rollLoyaltyCheck(retainer)}
                  title="Roll loyalty check (2d6 vs {retainer.loyalty})"
                >
                  Loyalty: {retainer.loyalty}
                </button>
              {/if}
            </div>
            {#if isOwner || isGM}
              <button
                class="btn-ghost text-xs text-red-700 hover:text-red-900"
                disabled={dismissing === retainer.id}
                on:click={() => dismissRetainer(retainer)}
              >
                {dismissing === retainer.id ? 'Dismissing...' : 'Dismiss'}
              </button>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>
