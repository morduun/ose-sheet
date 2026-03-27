<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import Modal from '$lib/components/shared/Modal.svelte';
  import Badge from '$lib/components/shared/Badge.svelte';

  export let character;
  export let isGM = false;
  export let isOwner = false;
  export let rollDice = null;

  let animals = [];
  let loading = true;
  let error = '';

  // Add animal modal
  let showAddModal = false;
  let animalTypes = [];
  let selectedType = '';
  let customName = '';
  let animalSource = 'purchased';
  let adding = false;

  // Custom animal stats
  let customSpecies = '';
  let customHP = 4;
  let customAC = 7;
  let customHD = 1;
  let customMorale = 6;
  let customMovement = 120;
  let customEncMovement = '';
  let customBaseLoad = '';
  let customMaxLoad = '';

  $: isCustom = selectedType === 'custom';

  // HP edit
  let hpEditId = null;
  let hpDelta = '';

  // Load item modal
  let showLoadModal = false;
  let loadAnimalId = null;
  let charItems = [];
  let loadItemId = null;
  let loadQty = 1;
  let loadingItem = false;

  const EQUIP_LABELS = {
    saddle: { name: 'Saddle & Bridle', cost: 25 },
    barding: { name: 'Horse Barding', cost: 150, note: 'AC 5, weighs 600cn' },
    saddlebags: { name: 'Saddle Bags', cost: 5, note: '300cn capacity' },
    dog_armor: { name: 'Dog Armour', cost: 25, note: 'AC 6' },
    dog_pack: { name: 'Dog Pack', cost: 5, note: '50cn capacity' },
  };

  // Which equipment is available for which animal type
  const EQUIP_FOR_TYPE = {
    camel: ['saddle', 'saddlebags'],
    draft_horse: ['saddle', 'barding', 'saddlebags'],
    riding_horse: ['saddle', 'barding', 'saddlebags'],
    war_horse: ['saddle', 'barding', 'saddlebags'],
    mule: ['saddlebags'],
    hunting_dog: ['dog_pack'],
    war_dog: ['dog_armor', 'dog_pack'],
  };

  const TIER_COLORS = {
    none: '',
    unencumbered: 'text-green-700',
    encumbered: 'text-amber-700',
    overloaded: 'text-red-700 font-bold',
  };

  $: canEdit = isOwner || isGM;

  // Druid befriended HD tracking
  $: isDruid = (character?.character_class?.name === 'Druid');
  $: druidMaxHD = isDruid ? (character?.level ?? 1) * 2 : 0;
  $: befriendedHD = animals
    .filter(a => a.source === 'befriended')
    .reduce((sum, a) => sum + a.hit_dice, 0);

  onMount(async () => {
    try {
      animals = await api.get(`/characters/${character.id}/animals`);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  async function openAddModal() {
    showAddModal = true;
    selectedType = '';
    customName = '';
    animalSource = 'purchased';
    if (animalTypes.length === 0) {
      try {
        animalTypes = await api.get('/animal-types');
      } catch { animalTypes = []; }
    }
  }

  $: selectedTypeInfo = animalTypes.find(t => t.key === selectedType) || null;

  async function addAnimal() {
    if (!selectedType) return;
    if (isCustom && !customName.trim()) { alert('Custom animals need a name.'); return; }
    if (isCustom && !customSpecies.trim()) { alert('Custom animals need a species.'); return; }
    adding = true;
    try {
      const payload = {
        animal_type: isCustom ? customSpecies.trim().toLowerCase().replace(/\s+/g, '_') : selectedType,
        name: customName.trim() || null,
        source: animalSource,
      };
      if (isCustom) {
        payload.hp = parseInt(customHP) || 4;
        payload.ac = parseInt(customAC) || 7;
        payload.hit_dice = parseFloat(customHD) || 1;
        payload.morale = parseInt(customMorale) || 6;
        payload.base_movement = parseInt(customMovement) || 120;
        payload.encumbered_movement = customEncMovement ? parseInt(customEncMovement) : null;
        payload.base_load = customBaseLoad ? parseInt(customBaseLoad) : null;
        payload.max_load = customMaxLoad ? parseInt(customMaxLoad) : null;
      }
      const created = await api.post(`/characters/${character.id}/animals`, payload);
      animals = [...animals, created];
      showAddModal = false;
    } catch (e) {
      alert(e.message);
    } finally {
      adding = false;
    }
  }

  async function removeAnimal(animal) {
    if (!confirm(`Remove ${animal.name}?`)) return;
    try {
      await api.delete(`/characters/${character.id}/animals/${animal.id}`);
      animals = animals.filter(a => a.id !== animal.id);
    } catch (e) {
      alert(e.message);
    }
  }

  async function toggleEquipment(animal, key) {
    const current = animal.equipment[key] || false;
    try {
      const updated = await api.patch(`/characters/${character.id}/animals/${animal.id}`, {
        equipment: { [key]: !current },
      });
      const idx = animals.findIndex(a => a.id === animal.id);
      if (idx >= 0) animals[idx] = updated;
      animals = animals;
    } catch (e) {
      alert(e.message);
    }
  }

  function startHPEdit(id) { hpEditId = id; hpDelta = ''; }

  async function submitHP(animal) {
    const val = parseInt(hpDelta);
    if (isNaN(val) || val === 0) { hpEditId = null; return; }
    try {
      const updated = await api.patch(`/characters/${character.id}/animals/${animal.id}`, {
        hp_current: Math.max(0, Math.min(animal.hp_max, animal.hp_current + val)),
      });
      const idx = animals.findIndex(a => a.id === animal.id);
      if (idx >= 0) animals[idx] = updated;
      animals = animals;
    } catch (e) {
      alert(e.message);
    }
    hpEditId = null; hpDelta = '';
  }

  async function rollMorale(animal) {
    if (!rollDice || animal.morale == null) return;
    await rollDice('2d6', (roll) => {
      const result = roll <= animal.morale ? 'Holds!' : 'Flees!';
      return `${animal.name} ML ${animal.morale} \u2192 ${result}`;
    });
  }

  async function openLoadModal(animal) {
    loadAnimalId = animal.id;
    loadItemId = null;
    loadQty = 1;
    showLoadModal = true;
    try {
      charItems = await api.get(`/characters/${character.id}/items`);
    } catch { charItems = []; }
  }

  async function loadItem() {
    if (!loadItemId || !loadAnimalId) return;
    loadingItem = true;
    try {
      const updated = await api.post(`/characters/${character.id}/animals/${loadAnimalId}/load`, {
        item_id: parseInt(loadItemId),
        quantity: parseInt(loadQty) || 1,
      });
      const idx = animals.findIndex(a => a.id === loadAnimalId);
      if (idx >= 0) animals[idx] = updated;
      animals = animals;
      showLoadModal = false;
    } catch (e) {
      alert(e.message);
    } finally {
      loadingItem = false;
    }
  }

  async function unloadItem(animal, itemId, qty) {
    try {
      const updated = await api.post(`/characters/${character.id}/animals/${animal.id}/unload`, {
        item_id: itemId,
        quantity: qty,
      });
      const idx = animals.findIndex(a => a.id === animal.id);
      if (idx >= 0) animals[idx] = updated;
      animals = animals;
    } catch (e) {
      alert(e.message);
    }
  }

  function hpPct(c, m) { return m > 0 ? Math.round((c / m) * 100) : 0; }
</script>

<div>
  <div class="flex items-center justify-between mb-4">
    <h2 class="section-title mb-0 border-none">Animals</h2>
    {#if canEdit}
      <button class="btn text-xs" on:click={openAddModal}>+ Add Animal</button>
    {/if}
  </div>

  <!-- Druid HD budget -->
  {#if isDruid}
    <div class="panel mb-4 text-sm">
      <span class="text-ink-faint">Animal Friendship:</span>
      <span class="font-medium text-ink">{befriendedHD} / {druidMaxHD} HD</span>
      {#if befriendedHD >= druidMaxHD}
        <span class="text-red-700 text-xs ml-2">(at limit)</span>
      {/if}
    </div>
  {/if}

  {#if loading}
    <p class="text-ink-faint text-sm">Loading...</p>
  {:else if error}
    <p class="text-red-700 text-sm">{error}</p>
  {:else if animals.length === 0}
    <div class="panel text-center py-6">
      <p class="text-ink-faint text-sm">No animals.</p>
    </div>
  {:else}
    <div class="grid gap-3 sm:grid-cols-2">
      {#each animals as animal (animal.id)}
        {@const pct = hpPct(animal.hp_current, animal.hp_max)}
        {@const availEquip = EQUIP_FOR_TYPE[animal.animal_type] || []}
        <div class="panel">
          <!-- Header -->
          <div class="flex items-start justify-between mb-2">
            <div>
              <div class="font-medium text-ink">{animal.name}</div>
              <div class="text-xs text-ink-faint">
                {animal.animal_type.replace(/_/g, ' ')} · HD {animal.hit_dice}
                {#if animal.source === 'befriended'}
                  · <Badge label="Befriended" />
                {/if}
              </div>
            </div>
            <div class="text-right text-xs">
              <div class="text-ink-faint">AC</div>
              <div class="font-serif text-lg text-ink leading-none">{animal.effective_ac}</div>
            </div>
          </div>

          <!-- HP Bar -->
          <div class="mb-2">
            <div class="flex items-center justify-between text-xs mb-0.5">
              <span class="text-ink-faint">HP</span>
              {#if hpEditId === animal.id}
                <div class="flex items-center gap-1">
                  <input class="input w-14 text-center text-xs py-0" type="number" placeholder="+/-"
                    bind:value={hpDelta}
                    on:keydown={(e) => { if (e.key === 'Enter') submitHP(animal); if (e.key === 'Escape') hpEditId = null; }}
                  />
                  <button class="btn text-[10px] px-1 py-0" on:click={() => submitHP(animal)}>OK</button>
                </div>
              {:else}
                <!-- svelte-ignore a11y-click-events-have-key-events -->
                <!-- svelte-ignore a11y-no-static-element-interactions -->
                <span
                  class="font-medium cursor-pointer hover:underline {pct <= 25 ? 'text-red-800' : pct <= 50 ? 'text-amber-700' : 'text-ink'}"
                  on:click={() => canEdit && startHPEdit(animal.id)}
                >{animal.hp_current}/{animal.hp_max}</span>
              {/if}
            </div>
            <div class="h-1.5 bg-parchment-200 rounded-full overflow-hidden">
              <div class="h-full rounded-full transition-all {pct <= 25 ? 'bg-red-800' : pct <= 50 ? 'bg-amber-600' : 'bg-green-800'}"
                style="width: {pct}%"></div>
            </div>
          </div>

          <!-- Movement & Load -->
          <div class="grid grid-cols-2 gap-2 text-xs mb-2">
            <div>
              <span class="text-ink-faint">Move:</span>
              <span class="font-medium {TIER_COLORS[animal.load_tier]}">{animal.effective_movement}' ({Math.floor(animal.effective_movement / 3)}')</span>
            </div>
            {#if animal.base_load != null}
              <div>
                <span class="text-ink-faint">Load:</span>
                <span class="font-medium {TIER_COLORS[animal.load_tier]}">{animal.current_load} / {animal.base_load}</span>
                <span class="text-ink-faint text-[10px]">cn</span>
              </div>
            {/if}
          </div>

          <!-- Equipment toggles -->
          {#if availEquip.length > 0 && canEdit}
            <div class="flex flex-wrap gap-2 mb-2">
              {#each availEquip as key}
                {@const info = EQUIP_LABELS[key]}
                {@const equipped = animal.equipment[key] || false}
                <button
                  class="text-[10px] px-2 py-0.5 rounded border transition-colors
                    {equipped ? 'border-ink bg-parchment-100 text-ink' : 'border-ink-faint/30 text-ink-faint hover:bg-parchment-100'}"
                  on:click={() => toggleEquipment(animal, key)}
                  title="{info.name} ({info.cost}gp){info.note ? ' — ' + info.note : ''}"
                >{info.name}</button>
              {/each}
            </div>
          {/if}

          <!-- Container capacity indicator -->
          {#if animal.container_capacity > 0}
            <div class="mb-2">
              <div class="flex items-center justify-between text-[10px] text-ink-faint mb-1">
                <span>Pack: {animal.current_load} / {animal.container_capacity} cn</span>
                {#if canEdit}
                  <button class="btn-ghost text-[10px]" on:click={() => openLoadModal(animal)}>+ Load</button>
                {/if}
              </div>
              {#if (animal.inventory || []).length > 0}
                <div class="space-y-0.5">
                  {#each animal.inventory as entry}
                    <div class="flex items-center justify-between text-xs border-b border-parchment-200 pb-0.5 last:border-0">
                      <span class="text-ink">{entry.name ?? `Item #${entry.item_id}`} x{entry.quantity}</span>
                      {#if canEdit}
                        <button class="btn-ghost text-[10px]" on:click={() => unloadItem(animal, entry.item_id, entry.quantity)}>Unload</button>
                      {/if}
                    </div>
                  {/each}
                </div>
              {/if}
            </div>
          {/if}

          <!-- Actions -->
          <div class="flex items-center gap-2">
            {#if animal.morale != null}
              <button
                class="text-xs px-2 py-0.5 rounded border border-ink-faint/30 hover:bg-parchment-200 transition-colors"
                disabled={!rollDice}
                on:click={() => rollMorale(animal)}
                title="Roll morale (2d6 vs {animal.morale})"
              >ML: {animal.morale}</button>
            {/if}
            {#if canEdit}
              <button class="btn-danger text-xs ml-auto" on:click={() => removeAnimal(animal)}>Remove</button>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<!-- Add Animal Modal -->
<Modal bind:open={showAddModal} title="Add Animal">
  <div class="space-y-4">
    <div>
      <label class="block text-sm text-ink mb-1" for="at-type">Animal Type</label>
      <select id="at-type" class="input w-full" bind:value={selectedType}>
        <option value="">Select...</option>
        <optgroup label="Mounts & Burden">
          {#each animalTypes.filter(t => ['camel','draft_horse','riding_horse','war_horse','mule'].includes(t.key)) as t}
            <option value={t.key}>{t.name} ({t.cost_gp} gp)</option>
          {/each}
        </optgroup>
        <optgroup label="Dogs">
          {#each animalTypes.filter(t => ['hunting_dog','war_dog'].includes(t.key)) as t}
            <option value={t.key}>{t.name} ({t.cost_gp} gp)</option>
          {/each}
        </optgroup>
        <option value="custom">Custom Animal...</option>
      </select>
    </div>

    {#if selectedTypeInfo}
      <div class="panel bg-parchment-100/50 text-sm space-y-1">
        <div class="font-medium text-ink">{selectedTypeInfo.name}</div>
        <div class="grid grid-cols-3 gap-2 text-xs">
          <div><span class="text-ink-faint">AC:</span> {selectedTypeInfo.ac}</div>
          <div><span class="text-ink-faint">HD:</span> {selectedTypeInfo.hit_dice}</div>
          <div><span class="text-ink-faint">HP:</span> {selectedTypeInfo.hp}</div>
          <div><span class="text-ink-faint">Move:</span> {selectedTypeInfo.base_movement}'</div>
          <div><span class="text-ink-faint">ML:</span> {selectedTypeInfo.morale}</div>
          {#if selectedTypeInfo.base_load}
            <div><span class="text-ink-faint">Load:</span> {selectedTypeInfo.base_load}/{selectedTypeInfo.max_load}</div>
          {/if}
        </div>
        {#if Object.keys(selectedTypeInfo.abilities || {}).length > 0}
          <div class="text-xs text-ink-faint mt-1">
            {#each Object.entries(selectedTypeInfo.abilities) as [name, desc]}
              <div><strong>{name}:</strong> {desc}</div>
            {/each}
          </div>
        {/if}
      </div>
    {/if}

    {#if isCustom}
      <div class="panel bg-parchment-100/50 space-y-2">
        <div class="text-xs text-ink-faint">Enter stats for the custom animal (e.g. from a monster entry or druid befriending).</div>
        <div>
          <label class="text-[10px] text-ink-faint uppercase">Species <span class="text-red-700">*</span></label>
          <input class="input w-full text-sm" type="text" bind:value={customSpecies} placeholder="e.g. Bear, Giant Eagle, Wolf" />
        </div>
        <div class="grid grid-cols-4 gap-2">
          <div>
            <label class="text-[10px] text-ink-faint uppercase">HP</label>
            <input class="input w-full text-sm" type="number" min="1" bind:value={customHP} />
          </div>
          <div>
            <label class="text-[10px] text-ink-faint uppercase">AC</label>
            <input class="input w-full text-sm" type="number" bind:value={customAC} />
          </div>
          <div>
            <label class="text-[10px] text-ink-faint uppercase">HD</label>
            <input class="input w-full text-sm" type="number" step="0.5" min="0.5" bind:value={customHD} />
          </div>
          <div>
            <label class="text-[10px] text-ink-faint uppercase">Morale</label>
            <input class="input w-full text-sm" type="number" min="2" max="12" bind:value={customMorale} />
          </div>
        </div>
        <div class="grid grid-cols-4 gap-2">
          <div>
            <label class="text-[10px] text-ink-faint uppercase">Movement</label>
            <input class="input w-full text-sm" type="number" min="0" bind:value={customMovement} />
          </div>
          <div>
            <label class="text-[10px] text-ink-faint uppercase">Enc. Mv</label>
            <input class="input w-full text-sm" type="number" min="0" bind:value={customEncMovement} placeholder="—" />
          </div>
          <div>
            <label class="text-[10px] text-ink-faint uppercase">Base Load</label>
            <input class="input w-full text-sm" type="number" min="0" bind:value={customBaseLoad} placeholder="—" />
          </div>
          <div>
            <label class="text-[10px] text-ink-faint uppercase">Max Load</label>
            <input class="input w-full text-sm" type="number" min="0" bind:value={customMaxLoad} placeholder="—" />
          </div>
        </div>
      </div>
    {/if}

    <div>
      <label class="block text-sm text-ink mb-1" for="at-name">Name {#if isCustom}<span class="text-red-700">*</span>{:else}<span class="text-ink-faint">(optional)</span>{/if}</label>
      <input id="at-name" class="input w-full" type="text" bind:value={customName} placeholder="e.g. Shadowfax" />
    </div>

    <div>
      <label class="block text-sm text-ink mb-1" for="at-source">Source</label>
      <select id="at-source" class="input w-full" bind:value={animalSource}>
        <option value="purchased">Purchased</option>
        <option value="befriended">Befriended (Druid)</option>
        <option value="trained">Trained</option>
      </select>
    </div>

    <button class="btn w-full" on:click={addAnimal} disabled={!selectedType || adding}>
      {adding ? 'Adding...' : 'Add Animal'}
    </button>
  </div>
</Modal>

<!-- Load Item Modal -->
<Modal bind:open={showLoadModal} title="Load Item onto Animal">
  <div class="space-y-4">
    <div>
      <label class="text-xs text-ink-faint" for="li-item">Item</label>
      <select id="li-item" class="input w-full" bind:value={loadItemId}>
        <option value={null}>Select item...</option>
        {#each charItems.filter(e => !e.slot) as entry}
          <option value={entry.item.id}>{entry.item.name} (x{entry.quantity}{entry.item.weight ? `, ${entry.item.weight}cn ea` : ''})</option>
        {/each}
      </select>
    </div>
    <div>
      <label class="text-xs text-ink-faint" for="li-qty">Quantity</label>
      <input id="li-qty" class="input w-full" type="number" min="1" bind:value={loadQty} />
    </div>
    <button class="btn w-full" on:click={loadItem} disabled={!loadItemId || loadingItem}>
      {loadingItem ? 'Loading...' : 'Load onto Animal'}
    </button>
  </div>
</Modal>
