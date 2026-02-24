<script>
  /** Initial monster data for edit mode (null for create) */
  export let initialData = null;
  /** Called with the assembled payload */
  export let onSubmit;

  // --- Individual form fields (Svelte 5 reactivity safety) ---
  let name = initialData?.name || '';
  let description = initialData?.description || '';
  let ac = initialData?.ac != null ? String(initialData.ac) : '';
  let hitDice = initialData?.hit_dice || '';
  let hp = initialData?.hp != null ? String(initialData.hp) : '';
  let thac0 = initialData?.thac0 != null ? String(initialData.thac0) : '';
  let movementRate = initialData?.movement_rate || '';
  let morale = initialData?.morale != null ? String(initialData.morale) : '';
  let alignment = initialData?.alignment || 'Neutral';
  let xp = initialData?.xp != null ? String(initialData.xp) : '';

  // Saves
  const meta = initialData?.monster_metadata;
  let saveD = meta?.saves?.D != null ? String(meta.saves.D) : '';
  let saveW = meta?.saves?.W != null ? String(meta.saves.W) : '';
  let saveP = meta?.saves?.P != null ? String(meta.saves.P) : '';
  let saveB = meta?.saves?.B != null ? String(meta.saves.B) : '';
  let saveS = meta?.saves?.S != null ? String(meta.saves.S) : '';

  // Attacks — dynamic array
  let attackEntries = (meta?.attacks || []).map(a => ({ ...a }));
  if (attackEntries.length === 0) attackEntries = [{ name: '', damage: '', effects: '' }];

  // Number appearing
  let naWild = meta?.number_appearing?.wild || '';
  let naLair = meta?.number_appearing?.lair || '';

  // Treasure type — dynamic array of strings
  let ttEntries = meta?.treasure_type?.length ? [...meta.treasure_type] : [''];

  // Abilities — dynamic array of {name, description}
  let abilityEntries = meta?.abilities
    ? Object.entries(meta.abilities).map(([n, d]) => ({ name: n, description: d }))
    : [{ name: '', description: '' }];

  let submitting = false;
  let errorMsg = '';

  function addAttack() {
    attackEntries = [...attackEntries, { name: '', damage: '', effects: '' }];
  }
  function removeAttack(i) {
    attackEntries = attackEntries.filter((_, idx) => idx !== i);
  }

  function addTT() {
    ttEntries = [...ttEntries, ''];
  }
  function removeTT(i) {
    ttEntries = ttEntries.filter((_, idx) => idx !== i);
  }

  function addAbility() {
    abilityEntries = [...abilityEntries, { name: '', description: '' }];
  }
  function removeAbility(i) {
    abilityEntries = abilityEntries.filter((_, idx) => idx !== i);
  }

  function intOrNull(v) {
    const n = parseInt(v);
    return isNaN(n) ? null : n;
  }

  async function handleSubmit() {
    if (!name.trim()) { errorMsg = 'Name is required.'; return; }
    errorMsg = '';
    submitting = true;

    const saves = {};
    if (saveD !== '') saves.D = intOrNull(saveD);
    if (saveW !== '') saves.W = intOrNull(saveW);
    if (saveP !== '') saves.P = intOrNull(saveP);
    if (saveB !== '') saves.B = intOrNull(saveB);
    if (saveS !== '') saves.S = intOrNull(saveS);

    const attacks = attackEntries.filter(a => a.name.trim());
    const treasure_type = ttEntries.filter(t => t.trim());
    const abilities = {};
    for (const a of abilityEntries) {
      if (a.name.trim()) abilities[a.name.trim()] = a.description || '';
    }

    const monster_metadata = {};
    if (attacks.length) monster_metadata.attacks = attacks;
    if (Object.keys(saves).length) monster_metadata.saves = saves;
    if (naWild || naLair) monster_metadata.number_appearing = { wild: naWild, lair: naLair };
    if (treasure_type.length) monster_metadata.treasure_type = treasure_type;
    if (Object.keys(abilities).length) monster_metadata.abilities = abilities;

    const payload = {
      name: name.trim(),
      description: description || null,
      ac: intOrNull(ac),
      hit_dice: hitDice || null,
      hp: intOrNull(hp),
      thac0: intOrNull(thac0),
      movement_rate: movementRate || null,
      morale: intOrNull(morale),
      alignment: alignment || null,
      xp: intOrNull(xp),
      monster_metadata: Object.keys(monster_metadata).length ? monster_metadata : null,
    };

    try {
      await onSubmit(payload);
    } catch (e) {
      errorMsg = e.message;
    } finally {
      submitting = false;
    }
  }
</script>

<form on:submit|preventDefault={handleSubmit} class="space-y-6 max-w-3xl">
  {#if errorMsg}
    <p class="text-red-700 text-sm">{errorMsg}</p>
  {/if}

  <!-- Core Stats -->
  <div class="panel">
    <h2 class="section-title">Core Info</h2>
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div class="sm:col-span-2">
        <label class="block text-xs text-ink-faint mb-1" for="name">Name *</label>
        <input id="name" class="input w-full" type="text" bind:value={name} required />
      </div>
      <div class="sm:col-span-2">
        <label class="block text-xs text-ink-faint mb-1" for="description">Description (markdown)</label>
        <textarea id="description" class="input w-full" rows="3" bind:value={description}></textarea>
      </div>
    </div>
  </div>

  <!-- Combat Stats -->
  <div class="panel">
    <h2 class="section-title">Combat Stats</h2>
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
      <div>
        <label class="block text-xs text-ink-faint mb-1" for="ac">AC</label>
        <input id="ac" class="input w-full" type="number" bind:value={ac} />
      </div>
      <div>
        <label class="block text-xs text-ink-faint mb-1" for="hit_dice">Hit Dice</label>
        <input id="hit_dice" class="input w-full" type="text" bind:value={hitDice} placeholder="e.g. 3d8+1" />
      </div>
      <div>
        <label class="block text-xs text-ink-faint mb-1" for="hp">HP</label>
        <input id="hp" class="input w-full" type="number" bind:value={hp} />
      </div>
      <div>
        <label class="block text-xs text-ink-faint mb-1" for="thac0">THAC0</label>
        <input id="thac0" class="input w-full" type="number" bind:value={thac0} />
      </div>
      <div>
        <label class="block text-xs text-ink-faint mb-1" for="movement_rate">Movement</label>
        <input id="movement_rate" class="input w-full" type="text" bind:value={movementRate} placeholder="120' (40')" />
      </div>
      <div>
        <label class="block text-xs text-ink-faint mb-1" for="morale">Morale</label>
        <input id="morale" class="input w-full" type="number" bind:value={morale} min="2" max="12" />
      </div>
      <div>
        <label class="block text-xs text-ink-faint mb-1" for="alignment">Alignment</label>
        <select id="alignment" class="input w-full" bind:value={alignment}>
          <option value="Lawful">Lawful</option>
          <option value="Neutral">Neutral</option>
          <option value="Chaotic">Chaotic</option>
        </select>
      </div>
      <div>
        <label class="block text-xs text-ink-faint mb-1" for="xp">XP</label>
        <input id="xp" class="input w-full" type="number" bind:value={xp} />
      </div>
    </div>
  </div>

  <!-- Saves -->
  <div class="panel">
    <h2 class="section-title">Saving Throws</h2>
    <div class="grid grid-cols-5 gap-3">
      <div>
        <label class="block text-xs text-ink-faint mb-1 text-center" for="save_d">D</label>
        <input id="save_d" class="input w-full text-center" type="number" bind:value={saveD} placeholder="—" />
      </div>
      <div>
        <label class="block text-xs text-ink-faint mb-1 text-center" for="save_w">W</label>
        <input id="save_w" class="input w-full text-center" type="number" bind:value={saveW} placeholder="—" />
      </div>
      <div>
        <label class="block text-xs text-ink-faint mb-1 text-center" for="save_p">P</label>
        <input id="save_p" class="input w-full text-center" type="number" bind:value={saveP} placeholder="—" />
      </div>
      <div>
        <label class="block text-xs text-ink-faint mb-1 text-center" for="save_b">B</label>
        <input id="save_b" class="input w-full text-center" type="number" bind:value={saveB} placeholder="—" />
      </div>
      <div>
        <label class="block text-xs text-ink-faint mb-1 text-center" for="save_s">S</label>
        <input id="save_s" class="input w-full text-center" type="number" bind:value={saveS} placeholder="—" />
      </div>
    </div>
  </div>

  <!-- Attacks -->
  <div class="panel">
    <h2 class="section-title">Attacks</h2>
    {#each attackEntries as atk, i}
      <div class="grid grid-cols-[1fr_1fr_1fr_auto] gap-2 mb-2 items-end">
        <div>
          {#if i === 0}<label class="block text-xs text-ink-faint mb-1">Name</label>{/if}
          <input class="input w-full" type="text" bind:value={atk.name} placeholder="e.g. Bite" />
        </div>
        <div>
          {#if i === 0}<label class="block text-xs text-ink-faint mb-1">Damage</label>{/if}
          <input class="input w-full" type="text" bind:value={atk.damage} placeholder="e.g. 1d6" />
        </div>
        <div>
          {#if i === 0}<label class="block text-xs text-ink-faint mb-1">Effects</label>{/if}
          <input class="input w-full" type="text" bind:value={atk.effects} placeholder="Optional" />
        </div>
        <button type="button" class="btn-ghost text-xs px-2" on:click={() => removeAttack(i)} title="Remove attack">&times;</button>
      </div>
    {/each}
    <button type="button" class="btn-ghost text-xs mt-1" on:click={addAttack}>+ Add Attack</button>
  </div>

  <!-- Number Appearing & Treasure Type -->
  <div class="panel">
    <h2 class="section-title">Encounter Details</h2>
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
      <div>
        <label class="block text-xs text-ink-faint mb-1" for="na_wild">No. Appearing (Wild)</label>
        <input id="na_wild" class="input w-full" type="text" bind:value={naWild} placeholder="e.g. 2d6" />
      </div>
      <div>
        <label class="block text-xs text-ink-faint mb-1" for="na_lair">No. Appearing (Lair)</label>
        <input id="na_lair" class="input w-full" type="text" bind:value={naLair} placeholder="e.g. 2d6x10" />
      </div>
    </div>
    <h3 class="text-xs text-ink-faint mb-2">Treasure Type</h3>
    <div class="flex flex-wrap gap-2 items-end">
      {#each ttEntries as tt, i}
        <div class="flex items-center gap-1">
          <input class="input w-16 text-center" type="text" bind:value={ttEntries[i]} placeholder="e.g. B" />
          <button type="button" class="btn-ghost text-xs px-1" on:click={() => removeTT(i)}>&times;</button>
        </div>
      {/each}
      <button type="button" class="btn-ghost text-xs" on:click={addTT}>+ Add</button>
    </div>
  </div>

  <!-- Abilities -->
  <div class="panel">
    <h2 class="section-title">Abilities</h2>
    {#each abilityEntries as ab, i}
      <div class="mb-3 border-b border-parchment-200 pb-3 last:border-0 last:pb-0">
        <div class="flex items-center gap-2 mb-1">
          <input class="input flex-1" type="text" bind:value={ab.name} placeholder="Ability name" />
          <button type="button" class="btn-ghost text-xs px-2" on:click={() => removeAbility(i)}>&times;</button>
        </div>
        <textarea class="input w-full text-sm" rows="2" bind:value={ab.description} placeholder="Description (markdown)"></textarea>
      </div>
    {/each}
    <button type="button" class="btn-ghost text-xs mt-1" on:click={addAbility}>+ Add Ability</button>
  </div>

  <!-- Submit -->
  <div class="flex gap-3">
    <button type="submit" class="btn" disabled={submitting}>
      {submitting ? 'Saving...' : (initialData ? 'Save Changes' : 'Create Monster')}
    </button>
    <a href="/monsters" class="btn-ghost">Cancel</a>
  </div>
</form>
