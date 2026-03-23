<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import Modal from '$lib/components/shared/Modal.svelte';

  export let campaignId;
  export let isGM = false;
  export let characters = [];

  let vehicles = [];
  let loading = true;
  let error = '';

  // Add vehicle modal
  let showAddModal = false;
  let vehicleTypes = [];
  let selectedType = '';
  let customName = '';
  let addingVehicle = false;

  // Expanded vehicle (shows cargo)
  let expandedId = null;
  let cargo = [];
  let loadingCargo = false;

  // Add cargo modal
  let showCargoModal = false;
  let cargoVehicleId = null;
  let availableItems = [];
  let cargoSearch = '';
  let cargoQty = 1;
  let addingCargoId = null;

  // Take from cargo modal
  let showTakeModal = false;
  let takeVehicleId = null;
  let takeEntry = null;
  let takeCharacterId = null;
  let takeQty = 1;
  let takingItem = false;

  // HP edit
  let hpEditId = null;
  let hpDelta = '';

  // Type labels
  const TYPE_LABELS = { land: 'Land', seaworthy: 'Seaworthy', unseaworthy: 'Unseaworthy' };

  onMount(loadVehicles);

  async function loadVehicles() {
    loading = true;
    try {
      vehicles = await api.get(`/campaigns/${campaignId}/vehicles`);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  async function openAddModal() {
    showAddModal = true;
    selectedType = '';
    customName = '';
    if (vehicleTypes.length === 0) {
      try {
        vehicleTypes = await api.get(`/vehicle-types?campaign_id=${campaignId}`);
      } catch {
        vehicleTypes = [];
      }
    }
  }

  $: filteredTypes = vehicleTypes;
  $: selectedTypeInfo = vehicleTypes.find(t => t.key === selectedType) || null;

  async function addVehicle() {
    if (!selectedType) return;
    addingVehicle = true;
    try {
      await api.post(`/campaigns/${campaignId}/vehicles`, {
        base_type: selectedType,
        name: customName.trim() || null,
      });
      await loadVehicles();
      showAddModal = false;
    } catch (e) {
      alert(e.message);
    } finally {
      addingVehicle = false;
    }
  }

  async function deleteVehicle(v) {
    if (!confirm(`Delete ${v.name}? All cargo will be lost.`)) return;
    try {
      await api.delete(`/campaigns/${campaignId}/vehicles/${v.id}`);
      if (expandedId === v.id) expandedId = null;
      await loadVehicles();
    } catch (e) {
      alert(e.message);
    }
  }

  // --- HP ---

  function startHPEdit(id) {
    hpEditId = id;
    hpDelta = '';
  }

  async function submitHP(v) {
    const val = parseInt(hpDelta);
    if (isNaN(val) || val === 0) {
      hpEditId = null;
      hpDelta = '';
      return;
    }
    const newHP = Math.max(0, Math.min(v.hp_max, v.hp_current + val));
    try {
      await api.patch(`/campaigns/${campaignId}/vehicles/${v.id}`, { hp_current: newHP });
      v.hp_current = newHP;
      v.effective_movement = v.hp_max > 0 ? Math.floor(v.movement_rate * newHP / v.hp_max) : 0;
      vehicles = vehicles;
    } catch (e) {
      alert(e.message);
    }
    hpEditId = null;
    hpDelta = '';
  }

  function hpPct(current, max) {
    return max > 0 ? Math.round((current / max) * 100) : 0;
  }

  function hpColor(current, max) {
    const pct = hpPct(current, max);
    if (pct <= 25) return 'bg-red-700';
    if (pct <= 50) return 'bg-orange-600';
    return 'bg-green-600';
  }

  // --- Cargo ---

  async function toggleExpand(v) {
    if (expandedId === v.id) {
      expandedId = null;
      return;
    }
    expandedId = v.id;
    loadingCargo = true;
    try {
      cargo = await api.get(`/campaigns/${campaignId}/vehicles/${v.id}/cargo`);
    } catch {
      cargo = [];
    } finally {
      loadingCargo = false;
    }
  }

  async function openCargoModal(vehicleId) {
    cargoVehicleId = vehicleId;
    showCargoModal = true;
    cargoSearch = '';
    cargoQty = 1;
    try {
      availableItems = await api.get(`/items/?campaign_id=${campaignId}&limit=500`);
    } catch {
      availableItems = [];
    }
  }

  $: filteredCargoItems = availableItems.filter(i =>
    i.name.toLowerCase().includes(cargoSearch.toLowerCase())
  );

  async function addToCargo(item) {
    addingCargoId = item.id;
    try {
      cargo = await api.post(`/campaigns/${campaignId}/vehicles/${cargoVehicleId}/cargo`, {
        item_id: item.id,
        quantity: cargoQty,
      });
      await loadVehicles(); // refresh cargo_weight
      showCargoModal = false;
    } catch (e) {
      alert(e.message);
    } finally {
      addingCargoId = null;
    }
  }

  async function removeCargo(vehicleId, itemId) {
    try {
      await api.delete(`/campaigns/${campaignId}/vehicles/${vehicleId}/cargo/${itemId}`);
      cargo = cargo.filter(c => c.item.id !== itemId);
      await loadVehicles();
    } catch (e) {
      alert(e.message);
    }
  }

  function openTakeModal(vehicleId, entry) {
    takeVehicleId = vehicleId;
    takeEntry = entry;
    takeCharacterId = characters.length > 0 ? characters[0].id : null;
    takeQty = 1;
    showTakeModal = true;
  }

  async function takeFromCargo() {
    if (!takeCharacterId || !takeEntry) return;
    takingItem = true;
    try {
      await api.post(
        `/campaigns/${campaignId}/vehicles/${takeVehicleId}/cargo/${takeEntry.item.id}/take`,
        { character_id: parseInt(takeCharacterId), quantity: takeQty }
      );
      // Refresh cargo
      cargo = await api.get(`/campaigns/${campaignId}/vehicles/${takeVehicleId}/cargo`);
      await loadVehicles();
      showTakeModal = false;
    } catch (e) {
      alert(e.message);
    } finally {
      takingItem = false;
    }
  }

  function cargoPct(weight, capacity) {
    return capacity > 0 ? Math.min(100, (weight / capacity) * 100) : 0;
  }
</script>

<div>
  <div class="flex items-center justify-between mb-4">
    <h2 class="section-title mb-0 border-none">Vehicles</h2>
    {#if isGM}
      <button class="btn text-xs" on:click={openAddModal}>+ Add Vehicle</button>
    {/if}
  </div>

  {#if loading}
    <p class="text-ink-faint text-sm">Loading...</p>
  {:else if error}
    <p class="text-red-700 text-sm">{error}</p>
  {:else if vehicles.length === 0}
    <div class="panel text-center py-6">
      <p class="text-ink-faint text-sm">No vehicles. {isGM ? 'Click "+ Add Vehicle" to acquire one.' : ''}</p>
    </div>
  {:else}
    <div class="space-y-4">
      {#each vehicles as v (v.id)}
        {@const hp = hpPct(v.hp_current, v.hp_max)}
        {@const cpct = cargoPct(v.cargo_weight, v.cargo_capacity)}
        {@const isExpanded = expandedId === v.id}
        <div class="panel">
          <!-- Vehicle header -->
          <div class="flex items-start justify-between mb-2">
            <div class="flex-1">
              <div class="flex items-center gap-2">
                <button
                  class="font-serif text-lg text-ink hover:underline cursor-pointer text-left"
                  on:click={() => toggleExpand(v)}
                >{v.name}</button>
                <span class="text-[10px] px-1.5 py-0.5 rounded bg-ink/10 text-ink-faint uppercase tracking-wide font-medium">
                  {TYPE_LABELS[v.vehicle_type] ?? v.vehicle_type}
                </span>
              </div>
              {#if v.vehicle_metadata?.description}
                <p class="text-xs text-ink-faint mt-0.5">{v.vehicle_metadata.description}</p>
              {/if}
            </div>
            <div class="text-right shrink-0 ml-4">
              <div class="text-xs text-ink-faint">AC</div>
              <div class="font-serif text-2xl text-ink leading-none">{v.ac}</div>
            </div>
          </div>

          <!-- Stats row -->
          <div class="grid grid-cols-3 gap-4 mb-2 text-sm">
            <!-- Hull Points -->
            <div>
              <div class="flex items-center justify-between text-xs mb-0.5">
                <span class="text-ink-faint">Hull Points</span>
                {#if hpEditId === v.id}
                  <div class="flex items-center gap-1">
                    <input
                      class="input w-14 text-center text-xs py-0"
                      type="number"
                      placeholder="+/-"
                      bind:value={hpDelta}
                      on:keydown={(e) => { if (e.key === 'Enter') submitHP(v); if (e.key === 'Escape') { hpEditId = null; } }}
                      autofocus
                    />
                    <button class="btn text-[10px] px-1 py-0" on:click={() => submitHP(v)}>OK</button>
                  </div>
                {:else}
                  <!-- svelte-ignore a11y-click-events-have-key-events -->
                  <!-- svelte-ignore a11y-no-static-element-interactions -->
                  <span
                    class="font-medium cursor-pointer hover:underline {hp <= 25 ? 'text-red-800' : hp <= 50 ? 'text-orange-700' : 'text-ink'}"
                    on:click={() => isGM && startHPEdit(v.id)}
                    title={isGM ? 'Click to adjust HP' : ''}
                  >{v.hp_current} / {v.hp_max}</span>
                {/if}
              </div>
              <div class="w-full h-1.5 bg-parchment-200 rounded overflow-hidden">
                <div class="h-full rounded transition-all {hpColor(v.hp_current, v.hp_max)}" style="width: {hp}%"></div>
              </div>
            </div>

            <!-- Cargo -->
            <div>
              <div class="flex items-center justify-between text-xs mb-0.5">
                <span class="text-ink-faint">Cargo</span>
                <span class="font-medium text-ink">{v.cargo_weight.toLocaleString()} / {v.cargo_capacity.toLocaleString()}</span>
              </div>
              <div class="w-full h-1.5 bg-parchment-200 rounded overflow-hidden">
                <div
                  class="h-full rounded transition-all"
                  class:bg-green-600={cpct <= 50}
                  class:bg-yellow-600={cpct > 50 && cpct <= 75}
                  class:bg-orange-600={cpct > 75 && cpct <= 90}
                  class:bg-red-700={cpct > 90}
                  style="width: {cpct}%"
                ></div>
              </div>
            </div>

            <!-- Movement -->
            <div>
              <div class="flex items-center justify-between text-xs mb-0.5">
                <span class="text-ink-faint">Movement</span>
                <span class="font-medium text-ink">{v.effective_movement}' ({Math.floor(v.effective_movement / 3)}')</span>
              </div>
              {#if v.effective_movement < v.movement_rate}
                <div class="text-[10px] text-orange-700">Base: {v.movement_rate}' (reduced by hull damage)</div>
              {/if}
              {#if v.vehicle_metadata?.crew_min}
                <div class="text-[10px] text-ink-faint">Crew: {v.vehicle_metadata.crew_min}+</div>
              {/if}
            </div>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-2">
            <button
              class="btn-ghost text-xs"
              on:click={() => toggleExpand(v)}
            >{isExpanded ? 'Hide Cargo' : 'Show Cargo'}</button>
            {#if isGM}
              <button class="btn-ghost text-xs" on:click={() => openCargoModal(v.id)}>+ Load Cargo</button>
              <button class="btn-danger text-xs ml-auto" on:click={() => deleteVehicle(v)}>Delete</button>
            {/if}
          </div>

          <!-- Expanded cargo -->
          {#if isExpanded}
            <div class="mt-3 pt-3 border-t border-parchment-200">
              {#if loadingCargo}
                <p class="text-ink-faint text-xs">Loading cargo...</p>
              {:else if cargo.length === 0}
                <p class="text-ink-faint text-xs text-center py-2">Cargo hold is empty.</p>
              {:else}
                <div class="space-y-1">
                  {#each cargo as entry}
                    <div class="flex items-center justify-between text-sm border-b border-parchment-200 pb-1 last:border-0">
                      <div>
                        <span class="text-ink">{entry.item.name}</span>
                        <span class="text-xs text-ink-faint ml-1">×{entry.quantity}</span>
                        {#if entry.item.weight}
                          <span class="text-xs text-ink-faint ml-1">({entry.item.weight * entry.quantity} cn)</span>
                        {/if}
                      </div>
                      <div class="flex items-center gap-1">
                        <button
                          class="btn-ghost text-xs px-1.5 py-0.5"
                          on:click={() => openTakeModal(v.id, entry)}
                        >Take</button>
                        {#if isGM}
                          <button
                            class="btn-danger text-xs px-1.5 py-0.5"
                            on:click={() => removeCargo(v.id, entry.item.id)}
                          >✕</button>
                        {/if}
                      </div>
                    </div>
                  {/each}
                </div>
              {/if}
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>

<!-- Add Vehicle Modal -->
<Modal bind:open={showAddModal} title="Add Vehicle">
  <div class="space-y-4">
    <div>
      <label class="text-sm text-ink mb-1 block" for="vtype">Vehicle Type</label>
      <select id="vtype" class="input w-full" bind:value={selectedType}>
        <option value="">Select a type...</option>
        <optgroup label="Land">
          {#each vehicleTypes.filter(t => t.vehicle_class === 'land') as t}
            <option value={t.key}>{t.name} ({t.cost_gp} gp)</option>
          {/each}
        </optgroup>
        <optgroup label="Seaworthy">
          {#each vehicleTypes.filter(t => t.vehicle_class === 'seaworthy') as t}
            <option value={t.key}>{t.name} ({t.cost_gp.toLocaleString()} gp)</option>
          {/each}
        </optgroup>
        <optgroup label="Unseaworthy">
          {#each vehicleTypes.filter(t => t.vehicle_class === 'unseaworthy') as t}
            <option value={t.key}>{t.name} ({t.cost_gp.toLocaleString()} gp)</option>
          {/each}
        </optgroup>
      </select>
    </div>

    {#if selectedTypeInfo}
      <div class="panel bg-parchment-100/50 text-sm space-y-1">
        <div class="font-medium text-ink">{selectedTypeInfo.name}</div>
        <div class="text-xs text-ink-faint">{selectedTypeInfo.description}</div>
        <div class="grid grid-cols-3 gap-2 text-xs mt-2">
          <div><span class="text-ink-faint">HP:</span> {selectedTypeInfo.hp}</div>
          <div><span class="text-ink-faint">AC:</span> {selectedTypeInfo.ac}</div>
          <div><span class="text-ink-faint">Move:</span> {selectedTypeInfo.movement_rate}'</div>
          <div><span class="text-ink-faint">Cargo:</span> {selectedTypeInfo.cargo_capacity.toLocaleString()} cn</div>
          <div><span class="text-ink-faint">Crew:</span> {selectedTypeInfo.crew_min}+</div>
          {#if selectedTypeInfo.passengers}
            <div><span class="text-ink-faint">Pass.:</span> {selectedTypeInfo.passengers}</div>
          {/if}
        </div>
      </div>
    {/if}

    <div>
      <label class="text-sm text-ink mb-1 block" for="vname">Custom Name <span class="text-ink-faint">(optional)</span></label>
      <input id="vname" class="input w-full" type="text" bind:value={customName} placeholder="e.g. The Sea Witch" />
    </div>

    <button
      class="btn w-full"
      on:click={addVehicle}
      disabled={!selectedType || addingVehicle}
    >{addingVehicle ? 'Adding...' : 'Add Vehicle'}</button>
  </div>
</Modal>

<!-- Add Cargo Modal -->
<Modal bind:open={showCargoModal} title="Load Cargo">
  <div class="space-y-3">
    <input
      class="input w-full"
      type="text"
      placeholder="Search items..."
      bind:value={cargoSearch}
    />
    <div class="flex items-center gap-2">
      <label class="text-xs text-ink" for="cargo-qty">Quantity</label>
      <input id="cargo-qty" class="input w-16" type="number" min="1" bind:value={cargoQty} />
    </div>
    <div class="space-y-1 max-h-60 overflow-y-auto">
      {#each filteredCargoItems as item}
        <button
          class="w-full text-left panel py-2 px-3 hover:bg-parchment-100 transition-colors"
          on:click={() => addToCargo(item)}
          disabled={addingCargoId === item.id}
        >
          <div class="text-sm font-medium text-ink">{item.name}</div>
          <div class="text-xs text-ink-faint">
            {item.item_type}
            {#if item.weight} · {item.weight} cn{/if}
          </div>
        </button>
      {:else}
        <p class="text-ink-faint text-sm text-center py-4">No items found.</p>
      {/each}
    </div>
  </div>
</Modal>

<!-- Take from Cargo Modal -->
<Modal bind:open={showTakeModal} title="Take from Cargo">
  {#if takeEntry}
    <div class="space-y-4">
      <p class="text-sm text-ink">
        Take <strong>{takeEntry.item.name}</strong> (available: {takeEntry.quantity})
      </p>
      <div class="flex gap-4">
        <div class="flex-1">
          <label class="text-xs text-ink-faint" for="take-char">Character</label>
          <select id="take-char" class="input w-full" bind:value={takeCharacterId}>
            {#each characters as c}
              <option value={c.id}>{c.name}</option>
            {/each}
          </select>
        </div>
        <div class="w-20">
          <label class="text-xs text-ink-faint" for="take-qty">Qty</label>
          <input id="take-qty" class="input w-full" type="number" min="1" max={takeEntry.quantity} bind:value={takeQty} />
        </div>
      </div>
      <button class="btn w-full" on:click={takeFromCargo} disabled={takingItem || !takeCharacterId}>
        {takingItem ? 'Taking...' : 'Take'}
      </button>
    </div>
  {/if}
</Modal>
