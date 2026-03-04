<script>
  import { api } from '$lib/api.js';

  export let character;
  export let isGM = false;
  export let isOwner = false;
  export let rollDice = null;

  let mercTypes = null;
  let loading = false;
  let showHireForm = false;
  let saving = false;
  let removingId = null;
  let paying = false;

  // Hire form state
  let hireType = '';
  let hireRace = '';
  let hireQty = 1;

  $: mercs = character?.mercenaries ?? [];
  $: totalUnits = mercs.reduce((s, m) => s + m.quantity, 0);
  $: totalCost = mercs.reduce((s, m) => s + m.total_cost, 0);
  $: anyWartime = mercs.length > 0 && mercs.some(m => m.wartime);
  $: canEdit = isOwner || isGM;

  // Available races for selected type
  $: availableRaces = (() => {
    if (!mercTypes || !hireType) return [];
    const t = mercTypes.find(t => t.key === hireType);
    if (!t) return [];
    return Object.entries(t.costs)
      .filter(([, cost]) => cost !== null)
      .map(([race]) => race);
  })();

  // Cost preview
  $: hireCostPreview = (() => {
    if (!mercTypes || !hireType || !hireRace) return null;
    const t = mercTypes.find(t => t.key === hireType);
    if (!t) return null;
    const cost = t.costs[hireRace];
    if (cost == null) return null;
    return cost * hireQty;
  })();

  // Reset race when type changes
  $: if (hireType) {
    if (!availableRaces.includes(hireRace)) {
      hireRace = availableRaces[0] || '';
    }
  }

  async function ensureTypes() {
    if (mercTypes) return;
    loading = true;
    try {
      mercTypes = await api.get('/mercenary-types');
    } catch (e) {
      alert('Failed to load mercenary types');
    } finally {
      loading = false;
    }
  }

  function openHireForm() {
    ensureTypes();
    showHireForm = true;
    hireType = '';
    hireRace = '';
    hireQty = 1;
  }

  async function hire() {
    if (!hireType || !hireRace || hireQty < 1) return;
    saving = true;
    try {
      const unit = await api.post(`/characters/${character.id}/mercenaries`, {
        merc_type: hireType,
        race: hireRace,
        quantity: hireQty,
      });
      // Merge or add
      const idx = mercs.findIndex(m => m.merc_type === unit.merc_type && m.race === unit.race);
      if (idx >= 0) {
        mercs[idx] = unit;
      } else {
        mercs = [...mercs, unit];
      }
      character.mercenaries = mercs;
      character = character;
      showHireForm = false;
    } catch (e) {
      alert(e.message || 'Failed to hire mercenaries');
    } finally {
      saving = false;
    }
  }

  async function adjustQty(merc, delta) {
    const newQty = merc.quantity + delta;
    if (newQty < 1) return dismiss(merc);
    saving = true;
    try {
      const updated = await api.patch(`/characters/${character.id}/mercenaries/${merc.id}`, {
        quantity: newQty,
      });
      const idx = mercs.findIndex(m => m.id === merc.id);
      if (idx >= 0) mercs[idx] = updated;
      character.mercenaries = [...mercs];
      character = character;
    } catch (e) {
      alert(e.message || 'Failed to update');
    } finally {
      saving = false;
    }
  }

  async function dismiss(merc) {
    if (!confirm(`Dismiss all ${merc.name} (${merc.race})?`)) return;
    removingId = merc.id;
    try {
      await api.delete(`/characters/${character.id}/mercenaries/${merc.id}`);
      character.mercenaries = mercs.filter(m => m.id !== merc.id);
      character = character;
    } catch (e) {
      alert(e.message || 'Failed to dismiss');
    } finally {
      removingId = null;
    }
  }

  async function toggleWartime() {
    const newVal = !anyWartime;
    saving = true;
    try {
      const summary = await api.post(`/characters/${character.id}/mercenaries/set-wartime`, {
        wartime: newVal,
      });
      character.mercenaries = summary.units;
      character = character;
    } catch (e) {
      alert(e.message || 'Failed to toggle wartime');
    } finally {
      saving = false;
    }
  }

  async function payday() {
    if (!confirm(`Pay ${formatCost(totalCost)} gp for one month's mercenary wages?`)) return;
    paying = true;
    try {
      const result = await api.post(`/characters/${character.id}/mercenaries/payday`);
      character.platinum = result.platinum;
      character.gold = result.gold;
      character.electrum = result.electrum;
      character.silver = result.silver;
      character.copper = result.copper;
      character = character;
      alert(`Paid ${formatCost(result.cost_gp)} gp in mercenary wages.`);
    } catch (e) {
      alert(e.message || 'Failed to pay mercenaries');
    } finally {
      paying = false;
    }
  }

  async function rollMorale(merc) {
    if (!rollDice) return;
    await rollDice('2d6', (roll) => {
      const result = roll <= merc.morale ? 'Holds!' : 'Flees!';
      return `${merc.name} (${merc.race}) ML ${merc.morale} → ${result}`;
    });
  }

  function formatCost(cost) {
    return cost % 1 === 0 ? cost.toString() : cost.toFixed(1);
  }

  function capitalize(s) {
    return s.charAt(0).toUpperCase() + s.slice(1);
  }
</script>

<div>
  <!-- Header -->
  <div class="flex items-center justify-between mb-4 flex-wrap gap-2">
    <h2 class="section-title">
      Mercenaries ({totalUnits} unit{totalUnits !== 1 ? 's' : ''} | {formatCost(totalCost)} gp/mo)
    </h2>
    <div class="flex items-center gap-3">
      {#if mercs.length > 0 && canEdit}
        <label class="flex items-center gap-1.5 text-xs cursor-pointer select-none">
          <input
            type="checkbox"
            checked={anyWartime}
            on:change={toggleWartime}
            disabled={saving}
            class="accent-red-700"
          />
          Wartime (2x)
        </label>
      {/if}
      {#if mercs.length > 0 && canEdit}
        <button
          class="btn text-sm"
          disabled={paying || totalCost === 0}
          on:click={payday}
          title="Deduct {formatCost(totalCost)} gp from character wealth"
        >
          {paying ? 'Paying...' : 'Payday'}
        </button>
      {/if}
      {#if canEdit}
        <button class="btn text-sm" on:click={openHireForm}>
          + Hire
        </button>
      {/if}
    </div>
  </div>

  <!-- Hire Form -->
  {#if showHireForm}
    <div class="panel mb-4">
      <div class="flex items-center justify-between mb-3">
        <h3 class="font-medium text-sm">Hire Mercenaries</h3>
        <button class="btn-ghost text-xs" on:click={() => (showHireForm = false)}>Cancel</button>
      </div>
      {#if loading}
        <p class="text-ink-faint text-sm">Loading types...</p>
      {:else if mercTypes}
        <div class="grid gap-3 sm:grid-cols-4">
          <!-- Type -->
          <div>
            <label class="text-xs text-ink-faint block mb-1">Type</label>
            <select bind:value={hireType} class="input text-sm w-full">
              <option value="">Select...</option>
              {#each mercTypes as t}
                <option value={t.key}>{t.name}</option>
              {/each}
            </select>
          </div>
          <!-- Race -->
          <div>
            <label class="text-xs text-ink-faint block mb-1">Race</label>
            <select bind:value={hireRace} class="input text-sm w-full" disabled={!hireType}>
              {#each availableRaces as race}
                <option value={race}>{capitalize(race)}</option>
              {/each}
            </select>
          </div>
          <!-- Qty -->
          <div>
            <label class="text-xs text-ink-faint block mb-1">Qty</label>
            <input
              type="number"
              min="1"
              bind:value={hireQty}
              class="input text-sm w-full"
            />
          </div>
          <!-- Hire -->
          <div class="flex items-end">
            <button
              class="btn text-sm w-full"
              disabled={!hireType || !hireRace || hireQty < 1 || saving}
              on:click={hire}
            >
              {#if hireCostPreview != null}
                Hire ({formatCost(hireCostPreview)} gp/mo)
              {:else}
                Hire
              {/if}
            </button>
          </div>
        </div>
        <!-- Type description -->
        {#if hireType}
          {@const info = mercTypes.find(t => t.key === hireType)}
          {#if info}
            <p class="text-xs text-ink-faint mt-2">
              AC {info.ac} | ML {info.morale} — {info.desc}
            </p>
          {/if}
        {/if}
      {/if}
    </div>
  {/if}

  <!-- Units Table -->
  {#if mercs.length === 0}
    <div class="panel text-center py-6">
      <p class="text-ink-faint text-sm">
        No mercenaries hired. They cost gold monthly and guard wilderness holdings.
      </p>
    </div>
  {:else}
    <div class="overflow-x-auto">
      <table class="w-full text-sm border-collapse">
        <thead>
          <tr class="border-b border-ink-faint/30 text-left text-xs text-ink-faint">
            <th class="py-1.5 pr-2">Type</th>
            <th class="py-1.5 pr-2">Race</th>
            <th class="py-1.5 pr-2 text-center">Qty</th>
            <th class="py-1.5 pr-2 text-center">AC</th>
            <th class="py-1.5 pr-2 text-center">ML</th>
            <th class="py-1.5 pr-2 text-right">Cost/mo</th>
            {#if canEdit}
              <th class="py-1.5 text-right">Actions</th>
            {/if}
          </tr>
        </thead>
        <tbody>
          {#each mercs as merc (merc.id)}
            <tr class="border-b border-ink-faint/10 hover:bg-parchment-200/50">
              <td class="py-1.5 pr-2">
                <span class="font-medium">{merc.name}</span>
              </td>
              <td class="py-1.5 pr-2 text-ink-faint">{capitalize(merc.race)}</td>
              <td class="py-1.5 pr-2 text-center">{merc.quantity}</td>
              <td class="py-1.5 pr-2 text-center">{merc.ac}</td>
              <td class="py-1.5 pr-2 text-center">
                <button
                  class="px-1.5 py-0.5 rounded border border-ink-faint/30 hover:bg-parchment-200 transition-colors"
                  disabled={!rollDice}
                  on:click={() => rollMorale(merc)}
                  title="Roll morale check (2d6 vs {merc.morale})"
                >
                  {merc.morale}
                </button>
              </td>
              <td class="py-1.5 pr-2 text-right">
                {formatCost(merc.total_cost)} gp
                {#if merc.wartime}
                  <span class="text-red-700 text-xs ml-0.5" title="Wartime rate">W</span>
                {/if}
              </td>
              {#if canEdit}
                <td class="py-1.5 text-right whitespace-nowrap">
                  <button
                    class="btn-ghost text-xs px-1"
                    disabled={saving}
                    on:click={() => adjustQty(merc, -1)}
                    title="Reduce by 1"
                  >-</button>
                  <button
                    class="btn-ghost text-xs px-1"
                    disabled={saving}
                    on:click={() => adjustQty(merc, 1)}
                    title="Add 1 more"
                  >+</button>
                  <button
                    class="btn-ghost text-xs text-red-700 hover:text-red-900 px-1 ml-1"
                    disabled={removingId === merc.id}
                    on:click={() => dismiss(merc)}
                    title="Dismiss all"
                  >{removingId === merc.id ? '...' : 'x'}</button>
                </td>
              {/if}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>
