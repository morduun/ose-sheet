<script>
  export let initialData = null;
  export let onSubmit;

  let key = initialData?.key || '';
  let name = initialData?.name || '';
  let ac = initialData?.ac ?? 9;
  let morale = initialData?.morale ?? 8;
  let description = initialData?.description || '';
  let raceCosts = initialData?.race_costs
    ? Object.entries(initialData.race_costs).map(([race, cost]) => ({ race, cost }))
    : [{ race: 'human', cost: 1 }];

  let submitting = false;
  let error = '';

  function addRace() {
    raceCosts = [...raceCosts, { race: '', cost: 1 }];
  }

  function removeRace(index) {
    raceCosts = raceCosts.filter((_, i) => i !== index);
  }

  function autoKey() {
    if (!key || key === initialData?.key) {
      key = name.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
    }
  }

  async function handleSubmit() {
    if (!name.trim()) { error = 'Name is required.'; return; }
    if (!key.trim()) { error = 'Key is required.'; return; }
    const validRaces = raceCosts.filter(r => r.race.trim());
    if (validRaces.length === 0) { error = 'At least one race is required.'; return; }

    submitting = true;
    error = '';
    try {
      const costs = {};
      for (const r of validRaces) {
        costs[r.race.trim().toLowerCase()] = parseFloat(r.cost) || 0;
      }
      await onSubmit({
        key: key.trim().toLowerCase().replace(/\s+/g, '_'),
        name: name.trim(),
        ac: parseInt(ac),
        morale: parseInt(morale),
        description: description.trim() || null,
        race_costs: costs,
      });
    } catch (e) {
      error = e.message;
      submitting = false;
    }
  }
</script>

<div class="flex flex-col gap-4">
  <div class="panel flex flex-col gap-4">
    <div class="grid grid-cols-2 gap-4">
      <div>
        <label class="block text-sm text-ink mb-1" for="mt-name">Name</label>
        <input id="mt-name" class="input w-full" type="text" bind:value={name} on:blur={autoKey} placeholder="Heavy Cavalry" />
      </div>
      <div>
        <label class="block text-sm text-ink mb-1" for="mt-key">Key</label>
        <input id="mt-key" class="input w-full font-mono" type="text" bind:value={key} placeholder="heavy_cavalry" />
      </div>
    </div>

    <div class="grid grid-cols-2 gap-4">
      <div>
        <label class="block text-sm text-ink mb-1" for="mt-ac">Armour Class</label>
        <input id="mt-ac" class="input w-full" type="number" bind:value={ac} />
      </div>
      <div>
        <label class="block text-sm text-ink mb-1" for="mt-morale">Morale</label>
        <input id="mt-morale" class="input w-full" type="number" min="2" max="12" bind:value={morale} />
      </div>
    </div>

    <div>
      <label class="block text-sm text-ink mb-1" for="mt-desc">Description</label>
      <textarea id="mt-desc" class="input w-full resize-none" rows="2" bind:value={description} placeholder="Equipment and capabilities..."></textarea>
    </div>

    <div>
      <div class="flex items-center justify-between mb-2">
        <span class="text-sm text-ink">Race Costs <span class="text-ink-faint">(gp/month per unit)</span></span>
        <button type="button" class="btn-ghost text-xs" on:click={addRace}>+ Add Race</button>
      </div>
      <div class="space-y-2">
        {#each raceCosts as entry, i}
          <div class="flex gap-2 items-end">
            <div class="flex-1">
              <input class="input w-full text-sm" type="text" bind:value={entry.race} placeholder="Race name" />
            </div>
            <div class="w-24">
              <input class="input w-full text-sm" type="number" step="0.5" min="0" bind:value={entry.cost} placeholder="gp" />
            </div>
            <button type="button" class="btn-danger text-xs px-1.5 py-0.5" on:click={() => removeRace(i)}>X</button>
          </div>
        {/each}
      </div>
    </div>
  </div>

  {#if error}
    <p class="text-red-700 text-sm">{error}</p>
  {/if}

  <div class="flex gap-3">
    <button class="btn" on:click={handleSubmit} disabled={submitting}>
      {submitting ? 'Saving...' : 'Save Mercenary Type'}
    </button>
    <a href="/mercenaries" class="btn-ghost">Cancel</a>
  </div>
</div>
