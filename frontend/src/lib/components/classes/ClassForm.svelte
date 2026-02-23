<script>
  import LevelGrid from './LevelGrid.svelte';
  import AbilityEditor from './AbilityEditor.svelte';

  /** Initial class_data object (deep-cloned internally) */
  export let initialData = null;
  export let initialName = '';
  export let initialDescription = '';
  /** Called with the final payload {name, description, is_default, campaign_id, class_data} */
  export let onSubmit;

  // --- Default class_data factory ---
  function fill(n, v) { return Array(n).fill(v); }

  function makeDefaults(maxLvl = 14) {
    return {
      max_level: maxLvl,
      hit_dice: '1d8',
      hp_bonus_post_9th: 0,
      armor: 'any',
      shields: 'any',
      weapons: 'any',
      languages: ['Common'],
      prime_requisite: [],
      Requirements: {},
      thac0: fill(maxLvl, 20),
      xp: fill(maxLvl, 0),
      saving_throws: {
        death: fill(maxLvl, 16),
        wands: fill(maxLvl, 16),
        paralyze: fill(maxLvl, 16),
        breath: fill(maxLvl, 16),
        spells: fill(maxLvl, 16),
      },
      spells: {
        '1st': fill(maxLvl, 0), '2nd': fill(maxLvl, 0), '3rd': fill(maxLvl, 0),
        '4th': fill(maxLvl, 0), '5th': fill(maxLvl, 0), '6th': fill(maxLvl, 0),
      },
      turning: {
        '1hd': fill(maxLvl, '-'), '2hd': fill(maxLvl, '-'), '2+hd': fill(maxLvl, '-'),
        '3hd': fill(maxLvl, '-'), '4hd': fill(maxLvl, '-'), '5hd': fill(maxLvl, '-'),
        '6hd': fill(maxLvl, '-'), '7hd': fill(maxLvl, '-'), '8hd': fill(maxLvl, '-'),
        '9hd': fill(maxLvl, '-'), '10hd': fill(maxLvl, '-'), '11hd': fill(maxLvl, '-'),
        '12+hd': fill(maxLvl, '-'),
      },
      thief_skills: {
        climb_surface: fill(maxLvl, 0), find_traps: fill(maxLvl, 0),
        hear_noise: fill(maxLvl, 1), hide_shadows: fill(maxLvl, 0),
        move_silent: fill(maxLvl, 0), open_locks: fill(maxLvl, 0),
        pick_pockets: fill(maxLvl, 0), falling: fill(maxLvl, 0),
        tightrope_walking: fill(maxLvl, 0), assassination: fill(maxLvl, 0),
        agile_fighting: fill(maxLvl, 0), hide_undergrowth: fill(maxLvl, 0),
        lay_on_hands: fill(maxLvl, 0), tracking: fill(maxLvl, 0),
      },
      abilities: {},
      domain: '',
      spell_lists: [],
    };
  }

  // --- Source data (deep clone) ---
  const src = initialData ? JSON.parse(JSON.stringify(initialData)) : makeDefaults();

  // --- Individual form fields (no shared reactive object) ---
  let name = initialName;
  let description = initialDescription;
  let hitDice = src.hit_dice || '1d8';
  let hpBonus = src.hp_bonus_post_9th ?? 0;
  let maxLevel = src.max_level || 14;
  let armor = src.armor || 'any';
  let shields = src.shields || 'any';
  let weapons = src.weapons || 'any';
  let languagesStr = (src.languages || []).join(', ');
  let domainText = src.domain || '';

  // --- Array data for grids (each is its own object, not sharing a parent) ---
  function padArr(arr, len, defaultVal) {
    if (!arr) return fill(len, defaultVal);
    if (arr.length >= len) return arr.slice(0, len);
    return [...arr, ...fill(len - arr.length, defaultVal)];
  }

  let progressionData = {
    thac0: padArr(src.thac0, maxLevel, 20),
    xp: padArr(src.xp, maxLevel, 0),
  };

  let savingThrows = {};
  for (const k of ['death', 'wands', 'paralyze', 'breath', 'spells']) {
    savingThrows[k] = padArr(src.saving_throws?.[k], maxLevel, 16);
  }

  let spellSlots = {};
  for (const k of ['1st', '2nd', '3rd', '4th', '5th', '6th']) {
    spellSlots[k] = padArr(src.spells?.[k], maxLevel, 0);
  }

  const turningKeys = ['1hd','2hd','2+hd','3hd','4hd','5hd','6hd','7hd','8hd','9hd','10hd','11hd','12+hd'];
  let turning = {};
  for (const k of turningKeys) {
    turning[k] = padArr(src.turning?.[k], maxLevel, '-');
  }

  const thiefKeys = [
    'climb_surface','find_traps','hear_noise','hide_shadows','move_silent','open_locks','pick_pockets',
    'falling','tightrope_walking','assassination','agile_fighting','hide_undergrowth','lay_on_hands','tracking',
  ];
  let thiefSkills = {};
  for (const k of thiefKeys) {
    thiefSkills[k] = padArr(src.thief_skills?.[k], maxLevel, k === 'hear_noise' ? 1 : 0);
  }

  // --- Spell list assignments ---
  const SPELL_LISTS = ['cleric', 'druid', 'illusionist', 'magic-user'];
  let spellListEntries = (src.spell_lists || []).map(e => ({ list: e.list, from_level: e.from_level }));

  function addSpellList() {
    const used = new Set(spellListEntries.map(e => e.list));
    const next = SPELL_LISTS.find(l => !used.has(l)) || SPELL_LISTS[0];
    spellListEntries = [...spellListEntries, { list: next, from_level: 1 }];
  }

  function removeSpellList(index) {
    spellListEntries = spellListEntries.filter((_, i) => i !== index);
  }

  // --- Attribute constants ---
  const ATTRIBUTES = ['STR', 'INT', 'WIS', 'DEX', 'CON', 'CHA'];
  const HIT_DICE_OPTIONS = ['1d4', '1d6', '1d8'];

  // --- Prime requisite editor ---
  let primeReqEntries = [...(src.prime_requisite || [])];

  function addPrimeReq() {
    const used = new Set(primeReqEntries);
    const next = ATTRIBUTES.find(a => !used.has(a)) || ATTRIBUTES[0];
    primeReqEntries = [...primeReqEntries, next];
  }

  function removePrimeReq(index) {
    primeReqEntries = primeReqEntries.filter((_, i) => i !== index);
  }

  // --- Attribute requirements editor ---
  let reqEntries = Object.entries(src.Requirements || {}).map(([attr, min]) => ({ attr, min }));

  function addRequirement() {
    const used = new Set(reqEntries.map(e => e.attr));
    const next = ATTRIBUTES.find(a => !used.has(a)) || ATTRIBUTES[0];
    reqEntries = [...reqEntries, { attr: next, min: 9 }];
  }

  function removeRequirement(index) {
    reqEntries = reqEntries.filter((_, i) => i !== index);
  }

  // --- Tab state ---
  const tabs = ['Basics', 'Progression', 'Magic', 'Skills & Abilities'];
  let activeTab = 'Basics';

  // --- Row definitions for grids ---
  const saveRows = [
    { key: 'death', label: 'Death / Poison' },
    { key: 'wands', label: 'Wands' },
    { key: 'paralyze', label: 'Paralyze / Petrify' },
    { key: 'breath', label: 'Breath Attacks' },
    { key: 'spells', label: 'Spells / Rods / Staves' },
  ];
  const thac0Rows = [{ key: 'thac0', label: 'THAC0' }];
  const xpRows = [{ key: 'xp', label: 'XP Required' }];
  const spellRows = [
    { key: '1st', label: '1st Level' }, { key: '2nd', label: '2nd Level' },
    { key: '3rd', label: '3rd Level' }, { key: '4th', label: '4th Level' },
    { key: '5th', label: '5th Level' }, { key: '6th', label: '6th Level' },
  ];
  const turningRows = [
    { key: '1hd', label: '1 HD' }, { key: '2hd', label: '2 HD' },
    { key: '2+hd', label: '2+ HD' }, { key: '3hd', label: '3 HD' },
    { key: '4hd', label: '4 HD' }, { key: '5hd', label: '5 HD' },
    { key: '6hd', label: '6 HD' }, { key: '7hd', label: '7 HD' },
    { key: '8hd', label: '8 HD' }, { key: '9hd', label: '9 HD' },
    { key: '10hd', label: '10 HD' }, { key: '11hd', label: '11 HD' },
    { key: '12+hd', label: '12+ HD' },
  ];
  const thiefRows = [
    { key: 'climb_surface', label: 'Climb Surfaces' },
    { key: 'find_traps', label: 'Find Traps' },
    { key: 'hear_noise', label: 'Hear Noise' },
    { key: 'hide_shadows', label: 'Hide in Shadows' },
    { key: 'move_silent', label: 'Move Silently' },
    { key: 'open_locks', label: 'Open Locks' },
    { key: 'pick_pockets', label: 'Pick Pockets' },
    { key: 'falling', label: 'Falling' },
    { key: 'tightrope_walking', label: 'Tightrope Walking' },
    { key: 'assassination', label: 'Assassination' },
    { key: 'agile_fighting', label: 'Agile Fighting' },
    { key: 'hide_undergrowth', label: 'Hide in Undergrowth' },
    { key: 'lay_on_hands', label: 'Lay on Hands' },
    { key: 'tracking', label: 'Tracking' },
  ];

  // --- Max level change: resize all arrays ---
  let prevMaxLevel = maxLevel;
  function onMaxLevelChange() {
    const ml = parseInt(maxLevel) || 1;
    maxLevel = ml;
    if (ml === prevMaxLevel) return;
    prevMaxLevel = ml;

    // Resize all level-indexed arrays
    for (const k of ['thac0']) progressionData[k] = padArr(progressionData[k], ml, 20);
    for (const k of ['xp']) progressionData[k] = padArr(progressionData[k], ml, 0);
    progressionData = progressionData; // trigger reactivity

    for (const k in savingThrows) savingThrows[k] = padArr(savingThrows[k], ml, 16);
    savingThrows = savingThrows;

    for (const k in spellSlots) spellSlots[k] = padArr(spellSlots[k], ml, 0);
    spellSlots = spellSlots;

    for (const k in turning) turning[k] = padArr(turning[k], ml, '-');
    turning = turning;

    for (const k in thiefSkills) thiefSkills[k] = padArr(thiefSkills[k], ml, k === 'hear_noise' ? 1 : 0);
    thiefSkills = thiefSkills;

    if (abilityEditor) abilityEditor.resizeToLevel(ml);
  }

  // --- AbilityEditor ref ---
  let abilityEditor;

  // --- Submit handler ---
  let submitting = false;
  let error = '';

  async function handleSubmit() {
    if (!name.trim()) { error = 'Class name is required.'; return; }
    submitting = true;
    error = '';

    // Build Requirements object
    const reqObj = {};
    for (const e of reqEntries) {
      if (e.attr) reqObj[e.attr] = parseInt(e.min) || 0;
    }

    // Assemble class_data from individual fields
    const class_data = {
      name: name.trim(),
      max_level: maxLevel,
      hit_dice: hitDice,
      hp_bonus_post_9th: hpBonus,
      armor,
      shields,
      weapons,
      languages: languagesStr.split(',').map(s => s.trim()).filter(Boolean),
      prime_requisite: primeReqEntries.filter(Boolean),
      Requirements: reqObj,
      thac0: progressionData.thac0,
      xp: progressionData.xp,
      saving_throws: savingThrows,
      spells: spellSlots,
      turning,
      thief_skills: thiefSkills,
      abilities: abilityEditor ? abilityEditor.getAbilities() : (src.abilities || {}),
      ability_metadata: abilityEditor ? abilityEditor.getAbilityMetadata() : (src.ability_metadata || {}),
      domain: domainText,
      spell_lists: spellListEntries.filter(e => e.list),
    };

    try {
      await onSubmit({
        name: name.trim(),
        description: description.trim() || null,
        is_default: true,
        campaign_id: null,
        class_data,
      });
    } catch (e) {
      error = e.message;
      submitting = false;
    }
  }
</script>

<div class="flex flex-col gap-4">
  <!-- Tabs -->
  <div class="flex border-b border-ink-faint">
    {#each tabs as t}
      <button
        class={activeTab === t ? 'tab-active' : 'tab'}
        on:click={() => activeTab = t}
      >
        {t}
      </button>
    {/each}
  </div>

  <!-- Tab: Basics -->
  {#if activeTab === 'Basics'}
    <div class="panel flex flex-col gap-4">
      <div>
        <label class="block text-sm text-ink mb-1" for="class-name">Name</label>
        <input id="class-name" class="input w-full" type="text" bind:value={name} placeholder="Fighter" />
      </div>
      <div>
        <label class="block text-sm text-ink mb-1" for="class-desc">Description</label>
        <textarea id="class-desc" class="input w-full resize-none" rows="3" bind:value={description} placeholder="A brief description of the class..."></textarea>
      </div>
      <div class="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <div>
          <label class="block text-sm text-ink mb-1" for="hit-dice">Hit Dice</label>
          <select id="hit-dice" class="input w-full" bind:value={hitDice}>
            {#each HIT_DICE_OPTIONS as hd}
              <option value={hd}>{hd}</option>
            {/each}
          </select>
        </div>
        <div>
          <label class="block text-sm text-ink mb-1" for="hp-bonus">HP Bonus (post-9th)</label>
          <input id="hp-bonus" class="input w-full" type="number" bind:value={hpBonus} />
        </div>
        <div>
          <label class="block text-sm text-ink mb-1" for="max-level">Max Level</label>
          <input id="max-level" class="input w-full" type="number" min="1" max="36"
            bind:value={maxLevel} on:change={onMaxLevelChange} />
        </div>
        <div>
          <label class="block text-sm text-ink mb-1" for="armor">Armor</label>
          <input id="armor" class="input w-full" type="text" bind:value={armor} placeholder="any" />
        </div>
        <div>
          <label class="block text-sm text-ink mb-1" for="shields">Shields</label>
          <input id="shields" class="input w-full" type="text" bind:value={shields} placeholder="any" />
        </div>
        <div>
          <label class="block text-sm text-ink mb-1" for="weapons">Weapons</label>
          <input id="weapons" class="input w-full" type="text" bind:value={weapons} placeholder="any" />
        </div>
      </div>
      <div>
        <label class="block text-sm text-ink mb-1" for="languages">Languages (comma-separated)</label>
        <input id="languages" class="input w-full max-w-md" type="text" bind:value={languagesStr} placeholder="Common, Alignment" />
      </div>

      <!-- Prime Requisite -->
      <div>
        <span class="block text-sm text-ink mb-1">Prime Requisite (affects XP bonus)</span>
        {#if primeReqEntries.length > 0}
          <div class="flex flex-wrap gap-2 mb-2">
            {#each primeReqEntries as entry, i}
              <div class="flex items-center gap-1">
                <select class="input" bind:value={primeReqEntries[i]}>
                  {#each ATTRIBUTES as a}
                    <option value={a}>{a}</option>
                  {/each}
                </select>
                <button type="button" class="btn-danger text-xs px-2 py-0.5" on:click={() => removePrimeReq(i)}>
                  Remove
                </button>
              </div>
            {/each}
          </div>
        {/if}
        <button type="button" class="btn-ghost text-sm" on:click={addPrimeReq}>
          + Add Prime Requisite
        </button>
      </div>

      <!-- Attribute Requirements -->
      <div>
        <span class="block text-sm text-ink mb-1">Attribute Requirements (minimum scores to play this class)</span>
        {#if reqEntries.length > 0}
          <div class="flex flex-col gap-2 mb-2">
            {#each reqEntries as entry, i}
              <div class="flex items-center gap-2">
                <select class="input" bind:value={entry.attr}>
                  {#each ATTRIBUTES as a}
                    <option value={a}>{a}</option>
                  {/each}
                </select>
                <span class="text-sm text-ink-faint">min</span>
                <input type="number" class="input w-16 text-center" min="3" max="18" bind:value={entry.min} />
                <button type="button" class="btn-danger text-xs px-2 py-0.5" on:click={() => removeRequirement(i)}>
                  Remove
                </button>
              </div>
            {/each}
          </div>
        {/if}
        <button type="button" class="btn-ghost text-sm" on:click={addRequirement}>
          + Add Requirement
        </button>
      </div>
    </div>
  {/if}

  <!-- Tab: Progression -->
  {#if activeTab === 'Progression'}
    <div class="flex flex-col gap-4">
      <div>
        <h3 class="section-title">THAC0</h3>
        <LevelGrid rows={thac0Rows} columns={maxLevel} bind:data={progressionData} inputType="number" />
      </div>
      <div>
        <h3 class="section-title">XP Requirements</h3>
        <LevelGrid rows={xpRows} columns={maxLevel} bind:data={progressionData} inputType="number" />
      </div>
      <div>
        <h3 class="section-title">Saving Throws</h3>
        <LevelGrid rows={saveRows} columns={maxLevel} bind:data={savingThrows} inputType="number" />
      </div>
    </div>
  {/if}

  <!-- Tab: Magic -->
  {#if activeTab === 'Magic'}
    <div class="flex flex-col gap-4">
      <!-- Spell List Access -->
      <div>
        <h3 class="section-title">Spell List Access</h3>
        <p class="text-xs text-ink-faint mb-2">Which spell lists can this class draw from, and at what level?</p>
        {#if spellListEntries.length > 0}
          <div class="flex flex-col gap-2 mb-2">
            {#each spellListEntries as entry, i}
              <div class="flex items-center gap-2">
                <select class="input" bind:value={entry.list}>
                  {#each SPELL_LISTS as sl}
                    <option value={sl}>{sl}</option>
                  {/each}
                </select>
                <span class="text-sm text-ink-faint">from level</span>
                <input type="number" class="input w-16 text-center" min="1" max="36" bind:value={entry.from_level} />
                <button type="button" class="btn-danger text-xs px-2 py-0.5" on:click={() => removeSpellList(i)}>
                  Remove
                </button>
              </div>
            {/each}
          </div>
        {/if}
        <button type="button" class="btn-ghost text-sm" on:click={addSpellList}>
          + Add Spell List
        </button>
      </div>

      <div>
        <h3 class="section-title">Spell Slots per Level</h3>
        <LevelGrid rows={spellRows} columns={maxLevel} bind:data={spellSlots} inputType="number" />
      </div>
      <div>
        <h3 class="section-title">Turn Undead</h3>
        <LevelGrid rows={turningRows} columns={maxLevel} bind:data={turning} inputType="text" />
      </div>
    </div>
  {/if}

  <!-- Tab: Skills & Abilities -->
  {#if activeTab === 'Skills & Abilities'}
    <div class="flex flex-col gap-4">
      <div>
        <h3 class="section-title">Class Skills</h3>
        <LevelGrid rows={thiefRows} columns={maxLevel} bind:data={thiefSkills} inputType="number" />
      </div>
      <div>
        <h3 class="section-title">Abilities</h3>
        <AbilityEditor bind:this={abilityEditor} abilities={src.abilities || {}} abilityMetadata={src.ability_metadata || {}} maxLevel={maxLevel} />
      </div>
      <div>
        <label class="section-title block" for="domain">Domain</label>
        <textarea id="domain" class="input w-full resize-none" rows="4" bind:value={domainText} placeholder="Describe the class domain / stronghold rules..."></textarea>
      </div>
    </div>
  {/if}

  <!-- Error & Submit -->
  {#if error}
    <p class="text-red-700 text-sm">{error}</p>
  {/if}

  <div class="flex gap-3">
    <button class="btn" on:click={handleSubmit} disabled={submitting}>
      {submitting ? 'Saving...' : 'Save Class'}
    </button>
    <a href="/classes" class="btn-ghost">Cancel</a>
  </div>
</div>
