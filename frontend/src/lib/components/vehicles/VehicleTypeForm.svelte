<script>
  export let initialData = null;
  export let onSubmit;

  let key = initialData?.key || '';
  let name = initialData?.name || '';
  let vehicleClass = initialData?.vehicle_class || 'land';
  let hp = initialData?.hp ?? 10;
  let ac = initialData?.ac ?? 9;
  let cargoCapacity = initialData?.cargo_capacity ?? 4000;
  let movementRate = initialData?.movement_rate ?? 60;
  let costGp = initialData?.cost_gp ?? 0;
  let crewMin = initialData?.crew_min ?? 0;
  let passengers = initialData?.passengers ?? null;
  let description = initialData?.description || '';

  let submitting = false;
  let error = '';

  async function handleSubmit() {
    if (!name.trim()) { error = 'Name is required.'; return; }
    if (!key.trim()) { error = 'Key is required.'; return; }

    submitting = true;
    error = '';

    try {
      await onSubmit({
        key: key.trim().toLowerCase().replace(/\s+/g, '_'),
        name: name.trim(),
        vehicle_class: vehicleClass,
        hp: parseInt(hp),
        ac: parseInt(ac),
        cargo_capacity: parseInt(cargoCapacity),
        movement_rate: parseInt(movementRate),
        cost_gp: parseInt(costGp) || null,
        crew_min: parseInt(crewMin) || 0,
        passengers: passengers ? parseInt(passengers) : null,
        description: description.trim() || null,
      });
    } catch (e) {
      error = e.message;
      submitting = false;
    }
  }

  // Auto-generate key from name
  function autoKey() {
    if (!key || key === initialData?.key) {
      key = name.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
    }
  }
</script>

<div class="flex flex-col gap-4">
  <div class="panel flex flex-col gap-4">
    <div class="grid grid-cols-2 gap-4">
      <div>
        <label class="block text-sm text-ink mb-1" for="vt-name">Name</label>
        <input id="vt-name" class="input w-full" type="text" bind:value={name} on:blur={autoKey} placeholder="War Galley" />
      </div>
      <div>
        <label class="block text-sm text-ink mb-1" for="vt-key">Key <span class="text-ink-faint">(unique identifier)</span></label>
        <input id="vt-key" class="input w-full font-mono" type="text" bind:value={key} placeholder="war_galley" />
      </div>
    </div>

    <div>
      <label class="block text-sm text-ink mb-1" for="vt-class">Vehicle Class</label>
      <select id="vt-class" class="input w-full" bind:value={vehicleClass}>
        <option value="land">Land</option>
        <option value="seaworthy">Seaworthy</option>
        <option value="unseaworthy">Unseaworthy</option>
      </select>
    </div>

    <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
      <div>
        <label class="block text-sm text-ink mb-1" for="vt-hp">Hull Points</label>
        <input id="vt-hp" class="input w-full" type="number" min="1" bind:value={hp} />
      </div>
      <div>
        <label class="block text-sm text-ink mb-1" for="vt-ac">Armour Class</label>
        <input id="vt-ac" class="input w-full" type="number" min="0" bind:value={ac} />
      </div>
      <div>
        <label class="block text-sm text-ink mb-1" for="vt-move">Movement <span class="text-ink-faint">(ft/turn)</span></label>
        <input id="vt-move" class="input w-full" type="number" min="0" bind:value={movementRate} />
      </div>
      <div>
        <label class="block text-sm text-ink mb-1" for="vt-cost">Cost <span class="text-ink-faint">(gp)</span></label>
        <input id="vt-cost" class="input w-full" type="number" min="0" bind:value={costGp} />
      </div>
    </div>

    <div class="grid grid-cols-3 gap-4">
      <div>
        <label class="block text-sm text-ink mb-1" for="vt-cargo">Cargo Capacity <span class="text-ink-faint">(coins)</span></label>
        <input id="vt-cargo" class="input w-full" type="number" min="0" bind:value={cargoCapacity} />
      </div>
      <div>
        <label class="block text-sm text-ink mb-1" for="vt-crew">Min Crew</label>
        <input id="vt-crew" class="input w-full" type="number" min="0" bind:value={crewMin} />
      </div>
      <div>
        <label class="block text-sm text-ink mb-1" for="vt-pass">Passengers <span class="text-ink-faint">(optional)</span></label>
        <input id="vt-pass" class="input w-full" type="number" min="0" bind:value={passengers} placeholder="—" />
      </div>
    </div>

    <div>
      <label class="block text-sm text-ink mb-1" for="vt-desc">Description</label>
      <textarea id="vt-desc" class="input w-full resize-none" rows="3" bind:value={description} placeholder="Physical description, special rules, notes..."></textarea>
    </div>
  </div>

  {#if error}
    <p class="text-red-700 text-sm">{error}</p>
  {/if}

  <div class="flex gap-3">
    <button class="btn" on:click={handleSubmit} disabled={submitting}>
      {submitting ? 'Saving...' : 'Save Vehicle Type'}
    </button>
    <a href="/vehicles" class="btn-ghost">Cancel</a>
  </div>
</div>
