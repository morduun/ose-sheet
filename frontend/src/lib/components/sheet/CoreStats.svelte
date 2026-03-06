<script>
  import { api } from '$lib/api.js';
  import StatBox from '$lib/components/shared/StatBox.svelte';
  import Modal from '$lib/components/shared/Modal.svelte';
  import { WEAPON_QUALITIES, normalizeQualities } from '$lib/item-metadata.js';
  import Badge from '$lib/components/shared/Badge.svelte';

  export let character;
  export let isGM = false;
  export let isOwner = false;
  export let rollDice = null;

  let xpAward = '';
  let awardingXP = false;
  let levelingUp = false;
  let showLevelUpModal = false;
  let confirmFallen = false;
  let togglingAlive = false;
  let error = '';
  let successMsg = '';
  let warningToast = '';
  let warningTimer = null;

  function showWarning(msg) {
    warningToast = msg;
    if (warningTimer) clearTimeout(warningTimer);
    warningTimer = setTimeout(() => { warningToast = ''; warningTimer = null; }, 3000);
  }

  function checkAmmo(weapon) {
    if (weapon.weapon_type === 'ranged' && weapon.ammo_count != null && weapon.ammo_count <= 0) {
      showWarning(`Out of ${weapon.ammo_name || 'ammo'}! Cannot fire ${weapon.name}.`);
      return false;
    }
    return true;
  }

  async function decrementAmmo(weapon) {
    if (weapon.weapon_type !== 'ranged' || !weapon.ammo_item_id || weapon.ammo_count == null) return;
    const newCount = weapon.ammo_count - 1;
    try {
      await api.patch(`/characters/${character.id}/items/${weapon.ammo_item_id}`, {
        quantity: newCount,
      });
      weapon.ammo_count = newCount;
      character = character; // trigger reactivity
    } catch {
      // roll already happened — silently keep stale count
    }
  }

  // Per-weapon range selection: { weaponIndex: 'short'|'medium'|'long' }
  let rangeSelections = {};

  function parseRange(rangeStr) {
    if (!rangeStr || rangeStr === 'Melee') return null;
    const parts = rangeStr.split('/').map(Number);
    if (parts.length !== 3 || parts.some(isNaN)) return null;
    return { short: parts[0], medium: parts[1], long: parts[2] };
  }

  function getRangeMod(weaponIdx) {
    const sel = rangeSelections[weaponIdx] || 'medium';
    return sel === 'short' ? -1 : sel === 'long' ? 1 : 0;
  }

  function setRange(weaponIdx, band) {
    rangeSelections[weaponIdx] = band;
    rangeSelections = rangeSelections;
  }

  async function rollAttackAtRange(weapon, weaponIdx, action = null) {
    if (!rollDice) return;
    if (!checkAmmo(weapon)) return;
    const range = parseRange(weapon.range);
    const rangeMod = range ? getRangeMod(weaponIdx) : 0;
    const rangeName = rangeSelections[weaponIdx] || 'medium';
    let thac0 = weapon.effective_thac0 + rangeMod;
    if (action) thac0 -= action.hit_bonus;

    const rangeLabel = range ? `${rangeName} range` : '';

    await rollDice('1d20', (roll) => {
      const acHit = thac0 - roll;
      const prefix = action ? `${action.name} \u2192 ` : '';
      const suffix = rangeLabel ? ` (${rangeLabel})` : '';
      return `${prefix}Hits AC ${acHit}${suffix}`;
    });
    await decrementAmmo(weapon);
  }

  // Level-up HP state (independent lets — no reactive object)
  let hpDieRoll = 0;
  let hpConMod = 0;
  let hpTotal = 1;
  let hpRolled = false;
  let hpIsFlat = false;
  let hpFlatBonus = 0;
  let hpDieNotation = '';

  // Inline HP editing
  let hpDelta = '';
  let savingHP = false;
  let hpEditMode = false;

  $: canEditHP = isGM || isOwner;
  $: hpPct = character.hp_max > 0
    ? Math.round((character.hp_current / character.hp_max) * 100)
    : 0;
  $: hpColor = hpPct > 50 ? 'text-green-800' : hpPct > 25 ? 'text-amber-700' : 'text-red-800';
  $: hpBarColor = hpPct > 50 ? 'bg-green-800' : hpPct > 25 ? 'bg-amber-700' : 'bg-red-800';

  $: effectiveMove = character.combat_stats?.effective_movement ?? character.movement_rate;

  async function applyHPDelta(delta) {
    if (!delta || savingHP) return;
    savingHP = true;
    const newCurrent = Math.max(0, Math.min(character.hp_max, character.hp_current + delta));
    try {
      const updated = await api.patch(`/characters/${character.id}`, {
        hp_current: newCurrent,
      });
      character = { ...character, hp_current: updated.hp_current };
    } catch (e) {
      alert(e.message);
    } finally {
      savingHP = false;
    }
  }

  function handleHPSubmit() {
    const val = parseInt(hpDelta);
    if (isNaN(val) || val === 0) {
      hpEditMode = false;
      hpDelta = '';
      return;
    }
    applyHPDelta(val);
    hpDelta = '';
    hpEditMode = false;
  }

  function handleHPKeydown(e) {
    if (e.key === 'Enter') handleHPSubmit();
    if (e.key === 'Escape') {
      hpEditMode = false;
      hpDelta = '';
    }
  }

  // Ability check state
  let showAbilityCheckModal = false;
  let abilityCheckKey = '';
  let abilityCheckLabel = '';
  let abilityCheckScore = 10;
  let abilityCheckMod = 0;

  $: abilityCheckTarget = abilityCheckScore - abilityCheckMod;

  function handleAbilityClick(e, key, label) {
    const score = character[key] ?? 10;
    if (e.shiftKey) {
      // Shift+click: open modifier modal
      abilityCheckKey = key;
      abilityCheckLabel = label;
      abilityCheckScore = score;
      abilityCheckMod = 0;
      showAbilityCheckModal = true;
    } else {
      // Plain click: roll immediately, no modifier
      rollAbilityCheck(label, score, 0);
    }
  }

  function rollAbilityCheck(label, score, mod) {
    if (!rollDice) return;
    const target = score - mod;
    rollDice('1d20', (roll) => {
      const modStr = mod !== 0 ? ` (${score}${mod > 0 ? '-' : '+'}${Math.abs(mod)}=${target})` : '';
      return roll <= target
        ? `${label} check passed!${modStr}`
        : `${label} check failed!${modStr}`;
    });
  }

  function confirmAbilityCheck() {
    showAbilityCheckModal = false;
    rollAbilityCheck(abilityCheckLabel, abilityCheckScore, abilityCheckMod);
  }

  function handleAbilityModKeydown(e) {
    if (e.key === 'Enter') confirmAbilityCheck();
  }

  const abilities = [
    { key: 'strength', label: 'STR' },
    { key: 'intelligence', label: 'INT' },
    { key: 'wisdom', label: 'WIS' },
    { key: 'dexterity', label: 'DEX' },
    { key: 'constitution', label: 'CON' },
    { key: 'charisma', label: 'CHA' },
  ];

  const saveLabels = {
    death: 'Death / Poison',
    wands: 'Wands',
    paralyze: 'Paralysis / Stone',
    breath: 'Breath Attacks',
    spells: 'Spells / Rods / Staves',
  };

  const modifierLabels = {
    melee_adj: 'Melee',
    open_doors: 'Open Doors',
    additional_languages: 'Languages',
    literate: 'Literate',
    magic_saves: 'Magic Saves',
    ac_adj: 'AC',
    missile_adj: 'Missile',
    initiative_adj: 'Initiative',
    hp_modifier: 'HP',
    npc_reactions: 'Reactions',
    max_retainers: 'Max Retainers',
    retainer_loyalty: 'Loyalty',
  };

  // Values that are absolute (not signed +/-)
  const absoluteKeys = new Set(['max_retainers', 'retainer_loyalty']);

  function getModsForAbility(key) {
    if (!character.modifiers) return {};
    const raw = character.modifiers[key];
    if (!raw || typeof raw !== 'object') return {};
    const result = {};
    for (const [k, v] of Object.entries(raw)) {
      const label = modifierLabels[k] || k;
      result[label] = absoluteKeys.has(k) ? String(v) : v;
    }
    return result;
  }

  function getXPTable() {
    return character.character_class?.class_data?.xp ?? null;
  }

  function getXPThresholds() {
    const xpTable = getXPTable();
    if (!xpTable || !Array.isArray(xpTable)) return { min: 0, max: null };
    const min = xpTable[character.level - 1] ?? 0;
    const max = xpTable[character.level] ?? null;
    return { min, max };
  }

  function getXPProgress() {
    const { min, max } = getXPThresholds();
    if (max === null) return 100;
    const current = character.xp ?? 0;
    if (max === min) return 100;
    return Math.min(100, Math.max(0, Math.round(((current - min) / (max - min)) * 100)));
  }

  // Explicitly depend on character.level and character.xp so Svelte re-runs after level-up
  $: xpThresholds = (character.level, getXPThresholds());
  $: xpProgress = (character.level, character.xp, getXPProgress());
  $: canLevelUp = xpThresholds.max !== null && (character.xp ?? 0) >= xpThresholds.max;

  async function awardXP() {
    const amount = parseInt(xpAward);
    if (!amount || amount <= 0) return;
    awardingXP = true;
    error = '';
    try {
      const updated = await api.post(`/characters/${character.id}/award-xp`, { xp: amount });
      character = { ...character, xp: updated.xp };
      xpAward = '';
      successMsg = `Awarded ${amount} XP!`;
      setTimeout(() => (successMsg = ''), 3000);
    } catch (e) {
      error = e.message;
    } finally {
      awardingXP = false;
    }
  }

  function openLevelUpModal() {
    const cd = character.character_class?.class_data ?? {};
    const nextLevel = character.level + 1;

    hpConMod = character.modifiers?.constitution?.hp_modifier ?? 0;
    hpDieNotation = cd.hit_dice ?? '1d6';
    hpFlatBonus = cd.hp_bonus_post_9th ?? 0;
    hpRolled = false;
    hpDieRoll = 0;

    // After level 9 (i.e. reaching level 10+), use flat bonus instead of die
    hpIsFlat = nextLevel > 9;

    if (hpIsFlat) {
      // Flat bonus only, no CON modifier per OSE rules for post-name-level
      hpTotal = Math.max(1, hpFlatBonus);
    } else {
      hpTotal = Math.max(1, 1 + hpConMod);
    }

    showLevelUpModal = true;
  }

  async function rollHPDie() {
    if (!rollDice || hpIsFlat) return;
    const total = await rollDice(hpDieNotation, (roll) => {
      return `HP roll: ${roll}`;
    });
    // rollDice returns null/undefined if dice not initialized
    if (total == null) return;
    hpDieRoll = total;
    hpRolled = true;
    hpTotal = Math.max(1, total + hpConMod);
  }

  function updateHPTotal() {
    if (hpIsFlat) {
      hpTotal = Math.max(1, hpFlatBonus);
    } else {
      hpTotal = Math.max(1, hpDieRoll + hpConMod);
    }
  }

  async function confirmLevelUp() {
    levelingUp = true;
    error = '';
    try {
      const updated = await api.post(`/characters/${character.id}/level-up`, {
        hp_increase: hpTotal,
      });
      character = { ...character, ...updated };
      showLevelUpModal = false;
      successMsg = `Leveled up to ${updated.level}! (+${hpTotal} HP)`;
      setTimeout(() => (successMsg = ''), 3000);
    } catch (e) {
      error = e.message;
    } finally {
      levelingUp = false;
    }
  }

  async function setStatus(newStatus) {
    togglingAlive = true;
    error = '';
    try {
      const updated = await api.patch(`/characters/${character.id}`, {
        status: newStatus,
      });
      character = { ...character, status: updated.status, is_alive: updated.is_alive };
      confirmFallen = false;
    } catch (e) {
      error = e.message;
    } finally {
      togglingAlive = false;
    }
  }

  function handleStatusChange(e) {
    const newStatus = e.target.value;
    if (newStatus === 'fallen' && character.status !== 'fallen') {
      confirmFallen = true;
      // Reset select to current value — only apply after confirmation
      e.target.value = character.status || 'active';
    } else {
      setStatus(newStatus);
    }
  }

  // --- Special Attacks ---
  $: classData = character.character_class?.class_data ?? {};
  $: levelIndex = Math.max(0, (character.level ?? 1) - 1);

  // Union of class special attack names for sub-column headers
  $: classAttackNames = (() => {
    const abilityMeta = classData.ability_metadata ?? {};
    const names = [];
    for (const meta of Object.values(abilityMeta)) {
      if (!meta || meta.type !== 'special_attack') continue;
      for (const atk of (meta.attacks || [])) {
        if (!names.includes(atk.name)) names.push(atk.name);
      }
    }
    return names;
  })();

  $: hasClassAttacks = classAttackNames.length > 0;

  // Union of item special attack names across all equipped weapons
  $: itemAttackNames = (() => {
    const names = [];
    for (const w of (character.equipped_weapons || [])) {
      for (const atk of (w.item_special_attacks || [])) {
        if (!names.includes(atk.name)) names.push(atk.name);
      }
    }
    return names;
  })();

  $: hasItemAttacks = itemAttackNames.length > 0;

  // Get item special attack for a weapon by attack name, or null
  function getItemAttack(weapon, atkName) {
    for (const atk of (weapon.item_special_attacks || [])) {
      if (atk.name === atkName) return atk;
    }
    return null;
  }

  // Roll attack with item special attack bonuses
  async function rollItemAttack(weapon, weaponIdx, atk) {
    if (!rollDice) return;
    if (!checkAmmo(weapon)) return;
    const range = parseRange(weapon.range);
    const rangeMod = range ? getRangeMod(weaponIdx) : 0;
    const rangeName = rangeSelections[weaponIdx] || 'medium';
    const thac0 = weapon.effective_thac0 - (atk.hit_bonus || 0) + rangeMod;
    const rangeLabel = range ? `${rangeName} range` : '';
    await rollDice('1d20', (roll) => {
      const acHit = thac0 - roll;
      const suffix = rangeLabel ? ` (${rangeLabel})` : '';
      return `${atk.name} \u2192 Hits AC ${acHit}${suffix}`;
    });
    await decrementAmmo(weapon);
  }

  // Roll damage with item special attack damage bonus
  async function rollItemDamage(weapon, atk) {
    if (!rollDice) return;
    await rollDice(weapon.damage_dice, (total) => {
      const baseDmg = total + (weapon.damage_mod || 0) + (atk.damage_bonus || 0);
      const bonus = (atk.damage_bonus || 0);
      const bonusStr = bonus ? ` (+${bonus})` : '';
      return `${atk.name} \u2192 ${baseDmg} damage${bonusStr}`;
    });
  }

  // Item ability modifiers for ability score indicators
  $: itemAbilityMods = character.combat_stats?.item_ability_modifiers ?? {};

  const ABILITY_MOD_LABELS = {
    strength: 'STR', dexterity: 'DEX', wisdom: 'WIS',
    intelligence: 'INT', constitution: 'CON', charisma: 'CHA',
  };

  // Union of weapon quality damage names (Brace, Charge) across all equipped weapons
  $: qualityDamageNames = (() => {
    const names = [];
    for (const w of (character.equipped_weapons || [])) {
      const qualities = normalizeQualities(w.qualities);
      if (qualities.includes('brace') && !names.includes('Brace')) names.push('Brace');
      if (qualities.includes('charge') && !names.includes('Charge')) names.push('Charge');
    }
    return names;
  })();

  $: allDamageSubCols = [...classAttackNames, ...itemAttackNames, ...qualityDamageNames];
  $: allThac0SubCols = [...classAttackNames, ...itemAttackNames];
  $: hasSubCols = classAttackNames.length > 0 || itemAttackNames.length > 0 || qualityDamageNames.length > 0;

  // Per-weapon range modifiers (reactive on rangeSelections changes)
  $: rangeModifiers = (character.equipped_weapons || []).map((w, idx) => {
    if (!parseRange(w.range)) return 0;
    const sel = rangeSelections[idx] || 'medium';
    return sel === 'short' ? -1 : sel === 'long' ? 1 : 0;
  });

  const ACTIONABLE_QUALITIES = new Set(['brace', 'charge']);

  // Get class special attack details for a weapon + attack name, or null if not applicable
  function getClassAttack(weapon, atkName) {
    const abilityMeta = classData.ability_metadata ?? {};
    const wType = weapon.weapon_type;
    for (const meta of Object.values(abilityMeta)) {
      if (!meta || meta.type !== 'special_attack') continue;
      for (const atk of (meta.attacks || [])) {
        if (atk.name !== atkName) continue;
        if (atk.applies_to && !atk.applies_to.includes(wType)) return null;

        const dmgMult = Array.isArray(atk.damage_multiplier)
          ? atk.damage_multiplier[Math.min(levelIndex, atk.damage_multiplier.length - 1)]
          : (atk.damage_multiplier || null);

        const penalty = Array.isArray(atk.effect_penalty)
          ? atk.effect_penalty[Math.min(levelIndex, atk.effect_penalty.length - 1)]
          : (atk.effect_penalty ?? null);

        return {
          name: atk.name,
          hit_bonus: atk.hit_bonus || 0,
          damage_multiplier: dmgMult,
          effect: atk.effect || null,
          effect_penalty: penalty,
          condition: atk.condition || null,
        };
      }
    }
    return null;
  }

  // Get weapon quality damage action (Brace/Charge) for a weapon, or null if not applicable
  function getQualityDamageAction(weapon, qualityName) {
    const qualities = normalizeQualities(weapon.qualities);
    const key = qualityName.toLowerCase();
    if (!qualities.includes(key)) return null;
    const conditions = {
      brace: 'Double damage vs charging monsters',
      charge: 'Mounted, moving 60\u2032+',
    };
    return {
      name: qualityName,
      damage_multiplier: 2,
      condition: conditions[key] || qualityName,
    };
  }

  // Roll damage with class special attack modifiers
  async function rollDamageWithAction(weapon, action) {
    if (!rollDice) return;
    await rollDice(weapon.damage_dice, (total) => {
      const baseDmg = total + (weapon.damage_mod || 0);
      if (action.damage_multiplier) {
        const finalDmg = baseDmg * action.damage_multiplier;
        let msg = `${action.name} \u2192 ${finalDmg} damage (\u00d7${action.damage_multiplier})`;
        if (action.effect) {
          msg += ` \u00b7 ${action.effect}`;
          if (action.effect_penalty != null && action.effect_penalty !== 0)
            msg += ` (${action.effect_penalty})`;
        }
        return msg;
      }
      let msg = `${action.name} \u2192 ${baseDmg} damage`;
      if (action.effect) {
        msg += ` \u00b7 ${action.effect}`;
        if (action.effect_penalty != null && action.effect_penalty !== 0)
          msg += ` (${action.effect_penalty})`;
      }
      return msg;
    });
  }
</script>

<div class="space-y-6" class:opacity-75={character.status === 'fallen'}>
  <!-- Fallen banner -->
  {#if character.status === 'fallen'}
    <div class="text-center py-2 bg-red-900/10 border border-red-900/30 rounded">
      <span class="font-serif text-lg tracking-widest uppercase text-red-900/70">FALLEN</span>
    </div>
  {:else if character.status === 'independent'}
    <div class="text-center py-2 bg-ink/5 border border-ink/20 rounded">
      <span class="font-serif text-sm tracking-widest uppercase text-ink-faint">Acting Independently</span>
    </div>
  {/if}

  <!-- Header row -->
  <div class="flex flex-wrap items-center gap-4">
    <div>
      <h1 class="font-serif text-3xl text-ink">{character.name}</h1>
      <p class="text-ink-faint text-sm">
        {character.character_class?.name ?? character.combat_stats?.monster_name ?? 'Unknown'} · Level {character.level} · {character.alignment ?? 'Neutral'}
      </p>
    </div>
    <div class="ml-auto flex gap-2">
      <a href="/characters/{character.id}/edit" class="btn-ghost text-xs">Edit</a>
      <button
        class="btn text-xs"
        on:click={() => window.open(`/characters/${character.id}/print`, '_blank')}
      >
        Print
      </button>
      {#if isGM || isOwner}
        <select
          class="input text-xs py-1 px-2 w-auto"
          value={character.status || 'active'}
          on:change={handleStatusChange}
        >
          <option value="active">Active</option>
          <option value="independent">Independent</option>
          <option value="fallen">Fallen</option>
        </select>
      {:else}
        {#if character.status === 'independent'}
          <span class="text-[10px] px-1.5 py-0.5 rounded bg-ink/10 text-ink-faint uppercase tracking-wide font-medium">Independent</span>
        {:else if character.status === 'fallen'}
          <span class="text-[10px] px-1.5 py-0.5 rounded bg-red-900/20 text-red-900 uppercase tracking-wide font-medium">Fallen</span>
        {/if}
      {/if}
    </div>
  </div>

  <!-- Confirm fallen modal -->
  <Modal bind:open={confirmFallen} title="Mark as Fallen">
    <p class="text-sm text-ink mb-4">
      Mark <strong>{character.name}</strong> as fallen? They will be moved to the campaign graveyard.
    </p>
    {#if error}
      <p class="text-sm text-red-700 mb-3">{error}</p>
    {/if}
    <div class="flex gap-2 justify-end">
      <button class="btn-ghost text-xs" on:click={() => (confirmFallen = false)}>Cancel</button>
      <button
        class="btn-danger text-xs"
        disabled={togglingAlive}
        on:click={() => setStatus('fallen')}
      >
        {togglingAlive ? 'Saving…' : 'Confirm'}
      </button>
    </div>
  </Modal>

  <!-- Level Up Modal -->
  <Modal bind:open={showLevelUpModal} title="Level Up to {character.level + 1}">
    <div class="space-y-4">
      <p class="text-sm text-ink">
        <strong>{character.name}</strong> — {character.character_class?.name ?? character.combat_stats?.monster_name ?? 'Unknown'}
      </p>

      {#if hpIsFlat}
        <!-- Post-9th level: flat HP bonus, no die roll -->
        <div class="panel bg-parchment-100 text-center py-4">
          <div class="text-xs text-ink-faint uppercase tracking-wide mb-1">HP Bonus (Level 10+)</div>
          <div class="font-serif text-3xl text-ink">+{hpFlatBonus}</div>
          <div class="text-xs text-ink-faint mt-1">Flat bonus per level (no CON modifier)</div>
        </div>
      {:else}
        <!-- Normal level: hit die + CON -->
        <div class="flex items-center gap-4 justify-center">
          <!-- Die roll -->
          <div class="text-center">
            <div class="text-xs text-ink-faint uppercase tracking-wide mb-1">Hit Die</div>
            <button
              class="font-serif text-3xl text-ink cursor-pointer hover:bg-parchment-100 transition-colors rounded px-2"
              disabled={!rollDice}
              on:click={rollHPDie}
              title="Click to roll"
            >
              {#if hpRolled}
                {hpDieRoll}
              {:else}
                {hpDieNotation}
              {/if}
            </button>
            {#if !hpRolled}
              <div class="text-xs text-ink-faint mt-1">Click to roll</div>
            {:else}
              <div class="text-xs text-ink-faint mt-1">Rolled {hpDieNotation}</div>
            {/if}
          </div>

          <!-- Plus sign -->
          <div class="font-serif text-2xl text-ink-faint">+</div>

          <!-- CON modifier -->
          <div class="text-center">
            <div class="text-xs text-ink-faint uppercase tracking-wide mb-1">CON Mod</div>
            <div class="font-serif text-3xl text-ink">
              {hpConMod >= 0 ? '+' : ''}{hpConMod}
            </div>
          </div>
        </div>
      {/if}

      <!-- Editable HP total -->
      <div class="flex items-center justify-center gap-3 pt-2 border-t border-parchment-200">
        <label class="text-sm text-ink font-medium" for="hp-total">Total HP Gained</label>
        <input
          id="hp-total"
          class="input w-20 text-center font-serif text-xl"
          type="number"
          min="1"
          bind:value={hpTotal}
        />
      </div>
      <p class="text-xs text-ink-faint text-center">
        {character.hp_max} + {hpTotal} = {character.hp_max + hpTotal} HP
      </p>

      {#if error}
        <p class="text-sm text-red-700">{error}</p>
      {/if}

      <div class="flex gap-2 justify-end">
        <button class="btn-ghost text-xs" on:click={() => (showLevelUpModal = false)}>Cancel</button>
        <button
          class="btn text-xs"
          disabled={levelingUp}
          on:click={confirmLevelUp}
        >
          {levelingUp ? 'Leveling up...' : 'Confirm Level Up'}
        </button>
      </div>
    </div>
  </Modal>

  <!-- Ability Check Modifier Modal -->
  <Modal bind:open={showAbilityCheckModal} title="{abilityCheckLabel} Check">
    <div class="space-y-4">
      <div class="text-center">
        <div class="text-xs text-ink-faint uppercase tracking-wide mb-1">Target Score</div>
        <div class="font-serif text-4xl text-ink leading-none">{abilityCheckScore}</div>
      </div>

      <div class="text-center">
        <div class="text-xs text-ink-faint uppercase tracking-wide mb-2">Penalty / Bonus</div>
        <div class="flex items-center justify-center gap-2">
          <button
            class="hp-btn text-green-800 border-green-800/30 hover:bg-green-900/10"
            on:click={() => (abilityCheckMod -= 1)}
            title="Easier (-1 penalty)"
          >-</button>
          <input
            class="input w-16 text-center font-serif text-xl"
            type="number"
            bind:value={abilityCheckMod}
            on:keydown={handleAbilityModKeydown}
          />
          <button
            class="hp-btn text-red-800 border-red-800/30 hover:bg-red-900/10"
            on:click={() => (abilityCheckMod += 1)}
            title="Harder (+1 penalty)"
          >+</button>
        </div>
        <div class="text-xs text-ink-faint mt-1">
          + harder / - easier
        </div>
      </div>

      <div class="text-center pt-2 border-t border-parchment-200">
        <div class="text-xs text-ink-faint uppercase tracking-wide mb-1">Roll Under</div>
        <div class="font-serif text-3xl text-ink">
          {abilityCheckTarget}
        </div>
        {#if abilityCheckMod !== 0}
          <div class="text-xs text-ink-faint">
            {abilityCheckScore} {abilityCheckMod > 0 ? '-' : '+'} {Math.abs(abilityCheckMod)} = {abilityCheckTarget}
          </div>
        {/if}
      </div>

      <div class="flex gap-2 justify-end">
        <button class="btn-ghost text-xs" on:click={() => (showAbilityCheckModal = false)}>Cancel</button>
        <button
          class="btn text-xs"
          on:click={confirmAbilityCheck}
        >Roll d20</button>
      </div>
    </div>
  </Modal>

  <!-- XP Bar -->
  <div class="panel">
    <div class="flex items-center justify-between mb-2">
      <span class="text-sm text-ink font-medium">Level {character.level}</span>
      <span class="text-sm text-ink-faint">
        {character.xp ?? 0}{xpThresholds.max !== null ? ` / ${xpThresholds.max} XP` : ' XP (max level)'}
      </span>
    </div>
    <div class="h-3 bg-parchment-200 rounded-full overflow-hidden border border-parchment-300">
      <div
        class="h-full bg-ink rounded-full transition-all"
        style="width: {xpProgress}%"
      ></div>
    </div>

    {#if isGM}
      <div class="flex gap-2 mt-3 items-center">
        <input
          class="input w-28"
          type="number"
          min="1"
          placeholder="XP"
          bind:value={xpAward}
        />
        <button class="btn text-xs" on:click={awardXP} disabled={awardingXP}>
          Award XP
        </button>
        {#if canLevelUp}
          <button class="btn text-xs" on:click={openLevelUpModal} disabled={levelingUp}>
            Level Up ↑
          </button>
        {/if}
        {#if successMsg}
          <span class="text-sm text-green-700">{successMsg}</span>
        {/if}
        {#if error}
          <span class="text-sm text-red-700">{error}</span>
        {/if}
      </div>
    {/if}
  </div>

  <!-- Ability Scores + Saving Throws -->
  <div class="grid gap-6 sm:grid-cols-[1fr_auto]">
    <div class="panel">
      <h2 class="section-title">Ability Scores</h2>
      <div class="grid grid-cols-3 gap-3">
        {#each abilities as { key, label }}
          {@const itemMod = itemAbilityMods[key]}
          <button
            class="text-left cursor-pointer rounded-sm transition-colors hover:bg-parchment-100 h-full w-full"
            disabled={!rollDice}
            on:click={(e) => handleAbilityClick(e, key, label)}
            title="Click to roll · Shift+click for modifier"
          >
            <StatBox
              {label}
              score={character[key] ?? 10}
              modifiers={getModsForAbility(key)}
              clickable={!!rollDice}
            />
            {#if itemMod}
              <div class="text-[10px] text-center text-ink-faint -mt-1">
                ({itemMod > 0 ? '+' : ''}{itemMod} item)
              </div>
            {/if}
          </button>
        {/each}
      </div>
    </div>

    {#if character.saving_throws}
      <div class="panel sm:min-w-[200px]">
        <h2 class="section-title">Saving Throws</h2>
        <div class="grid gap-2">
          {#each Object.entries(saveLabels) as [key, label]}
            <button
              class="flex items-center justify-between border-b border-parchment-200 pb-1
                     cursor-pointer hover:bg-parchment-100 transition-colors text-left w-full"
              disabled={!rollDice}
              on:click={() => rollDice && rollDice('1d20', (roll) => {
                const target = character.saving_throws[key];
                return roll >= target
                  ? `Save made! (needed ${target})`
                  : `Save failed! (needed ${target})`;
              })}
            >
              <span class="text-sm text-ink">{label}</span>
              <span class="font-serif text-lg text-ink font-medium ml-4">
                {character.saving_throws[key] ?? '—'}
              </span>
            </button>
          {/each}
        </div>
      </div>
    {/if}
  </div>

  <!-- Combat Stats — 4 columns -->
  <div class="panel">
    <h2 class="section-title">Combat</h2>

    <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <!-- Column 1: AC -->
      <div class="text-center">
        <div class="text-xs text-ink-faint uppercase tracking-wide mb-0.5">Armor Class</div>
        <div class="font-serif text-4xl text-ink leading-none">{character.ac ?? '?'}</div>
        <div class="flex justify-center gap-3 mt-1 text-xs text-ink-faint">
          {#if character.rear_ac != null}
            <span>Rear {character.rear_ac}</span>
          {/if}
          {#if character.shieldless_ac != null}
            <span>No Shld {character.shieldless_ac}</span>
          {/if}
        </div>
      </div>

      <!-- Column 2: HP -->
      <div class="text-center">
        <div class="text-xs text-ink-faint uppercase tracking-wide mb-0.5">Hit Points</div>
        <div class="flex items-center justify-center gap-1.5">
          {#if canEditHP}
            <button
              class="hp-btn text-red-800 border-red-800/30 hover:bg-red-900/10"
              on:click={() => applyHPDelta(-1)}
              disabled={savingHP || character.hp_current <= 0}
              title="Take 1 damage"
            >-</button>
          {/if}
          <div>
            {#if hpEditMode}
              <div class="flex items-center gap-1">
                <input
                  class="input w-16 text-center font-serif text-xl py-0.5"
                  type="number"
                  placeholder="+/-"
                  bind:value={hpDelta}
                  on:keydown={handleHPKeydown}
                  autofocus
                />
                <button
                  class="btn text-xs px-2 py-1"
                  on:click={handleHPSubmit}
                  disabled={savingHP}
                >OK</button>
              </div>
            {:else}
              <!-- svelte-ignore a11y-click-events-have-key-events -->
              <!-- svelte-ignore a11y-no-static-element-interactions -->
              <div
                class="font-serif text-4xl {hpColor} leading-none"
                class:cursor-pointer={canEditHP}
                class:hover-highlight={canEditHP}
                style="border-radius: 0.25rem; padding: 0 0.25rem;"
                on:click={() => { if (canEditHP) { hpEditMode = true; hpDelta = ''; } }}
                title={canEditHP ? 'Click to adjust HP' : ''}
              >
                {character.hp_current ?? '?'}
              </div>
            {/if}
          </div>
          {#if canEditHP}
            <button
              class="hp-btn text-green-800 border-green-800/30 hover:bg-green-900/10"
              on:click={() => applyHPDelta(1)}
              disabled={savingHP || character.hp_current >= character.hp_max}
              title="Heal 1 HP"
            >+</button>
          {/if}
        </div>
        <div class="text-xs text-ink-faint mt-0.5">/ {character.hp_max ?? '?'}</div>
        <div class="h-1.5 bg-parchment-200 rounded-full overflow-hidden mt-1 mx-auto w-20">
          <div
            class="h-full {hpBarColor} rounded-full transition-all"
            style="width: {hpPct}%"
          ></div>
        </div>
      </div>

      <!-- Column 3: THAC0 -->
      <div class="text-center">
        <div class="text-xs text-ink-faint uppercase tracking-wide mb-0.5">THAC0</div>
        <div class="font-serif text-4xl text-ink leading-none">{character.thac0 ?? '?'}</div>
        <div class="flex justify-center gap-3 mt-1 text-xs text-ink-faint">
          <span>Melee {(character.thac0 ?? 19) - (character.modifiers?.strength?.melee_adj ?? 0)}</span>
          <span>Missile {(character.thac0 ?? 19) - (character.modifiers?.dexterity?.missile_adj ?? 0)}</span>
        </div>
      </div>

      <!-- Column 4: Movement -->
      <div class="text-center">
        <div class="text-xs text-ink-faint uppercase tracking-wide mb-0.5">Movement</div>
        <div class="font-serif text-4xl text-ink leading-none">{effectiveMove != null ? `${effectiveMove}'` : '?'}</div>
        <div class="text-xs text-ink-faint mt-1">{effectiveMove != null ? `(${Math.floor(effectiveMove / 3)}')` : ''} / round</div>
      </div>
    </div>

  </div>

  <!-- Equipped Weapons -->
  {#if character.equipped_weapons?.length}
    <div class="panel">
      <h2 class="section-title">Weapons</h2>
      <div class="overflow-x-auto -mx-2 px-2">
        <table class="w-full text-sm">
          {#if hasSubCols}
            <thead>
              <tr class="text-xs text-ink-faint uppercase tracking-wide">
                <th rowspan="2" class="text-left pb-0.5">Weapon</th>
                <th rowspan="2" class="text-center pb-0.5">Range</th>
                {#if allThac0SubCols.length > 0}
                  <th colspan={1 + allThac0SubCols.length} class="text-center pb-0 border-b border-parchment-200">THAC0</th>
                {:else}
                  <th rowspan="2" class="text-center pb-0.5">THAC0</th>
                {/if}
                <th colspan={1 + allDamageSubCols.length} class="text-center pb-0 border-b border-parchment-200">Damage</th>
              </tr>
              <tr class="text-[10px] text-ink-faint tracking-wide">
                {#if allThac0SubCols.length > 0}
                  <th class="text-center pb-1 font-normal">Normal</th>
                  {#each classAttackNames as atkName}
                    <th class="text-center pb-1 font-normal">{atkName}</th>
                  {/each}
                  {#each itemAttackNames as atkName}
                    <th class="text-center pb-1 font-normal">{atkName}</th>
                  {/each}
                {/if}
                <th class="text-center pb-1 font-normal">Normal</th>
                {#each classAttackNames as atkName}
                  <th class="text-center pb-1 font-normal">{atkName}</th>
                {/each}
                {#each itemAttackNames as atkName}
                  <th class="text-center pb-1 font-normal">{atkName}</th>
                {/each}
                {#each qualityDamageNames as qName}
                  <th class="text-center pb-1 font-normal">{qName}</th>
                {/each}
              </tr>
            </thead>
          {:else}
            <thead>
              <tr class="text-xs text-ink-faint uppercase tracking-wide">
                <th class="text-left pb-1">Weapon</th>
                <th class="text-center pb-1">Range</th>
                <th class="text-center pb-1">THAC0</th>
                <th class="text-center pb-1">Damage</th>
              </tr>
            </thead>
          {/if}
          <tbody>
            {#each character.equipped_weapons as w, idx}
              {@const range = parseRange(w.range)}
              {@const infoQualities = normalizeQualities(w.qualities).filter(q => !ACTIONABLE_QUALITIES.has(q))}
              <tr class="border-t border-parchment-200">
                <!-- Weapon name -->
                <td class="py-1">
                  <div>
                    <span class="text-ink">{w.name}</span>
                    {#if !w.identified && w.unidentified_name}
                      <Badge label="Unidentified" variant="gm" />
                    {/if}
                    {#if w.weapon_type === 'thrown'}
                      <span class="text-ink-faint text-xs">(Thrown)</span>
                    {/if}
                    {#if w.dual_wield_penalty != null}
                      <span class="text-xs text-ink-faint ml-1">{w.slot === 'main-hand' ? 'MH' : 'OH'}</span>
                    {/if}
                  </div>
                  {#if w.ammo_name}
                    <div class="text-xs {w.ammo_count <= 0 ? 'text-red-700 font-medium' : 'text-ink-faint'}">
                      ({w.ammo_name}: {w.ammo_count ?? '?'})
                    </div>
                  {/if}
                  {#if infoQualities.length}
                    <div class="flex flex-wrap gap-1 mt-0.5">
                      {#each infoQualities as q}
                        <span
                          class="text-[10px] px-1.5 py-0 rounded bg-parchment-200 text-ink-faint leading-relaxed"
                          title={WEAPON_QUALITIES[q] ?? ''}
                        >{q}</span>
                      {/each}
                    </div>
                  {/if}
                </td>

                <!-- Range selector -->
                <td class="text-center py-1">
                  {#if range}
                    <div class="flex items-center justify-center gap-0.5">
                      {#each [['short', 'S'], ['medium', 'M'], ['long', 'L']] as [band, label]}
                        <button
                          class="range-toggle"
                          class:range-active={(rangeSelections[idx] || 'medium') === band}
                          on:click={() => setRange(idx, band)}
                          title="{band}: {range[band]}'"
                        >{label}</button>
                      {/each}
                    </div>
                    <div class="text-[10px] text-ink-faint">{range[rangeSelections[idx] || 'medium']}'</div>
                  {:else}
                    <span class="text-ink-faint text-xs">Melee</span>
                  {/if}
                </td>

                <!-- Normal THAC0 -->
                <td class="text-center py-1">
                  <button
                    class="font-serif text-lg cursor-pointer hover:bg-parchment-100 transition-colors rounded px-1.5 -mx-1"
                    disabled={!rollDice}
                    on:click={() => rollAttackAtRange(w, idx)}
                  >
                    {w.effective_thac0 + (rangeModifiers[idx] || 0)}
                  </button>
                </td>

                <!-- Class attack THAC0 sub-columns -->
                {#each classAttackNames as atkName}
                  {@const atk = getClassAttack(w, atkName)}
                  <td class="text-center py-1">
                    {#if atk}
                      <button
                        class="font-serif text-lg cursor-pointer hover:bg-parchment-100 transition-colors rounded px-1.5 -mx-1"
                        disabled={!rollDice}
                        on:click={() => rollAttackAtRange(w, idx, atk)}
                        title={atk.condition || atk.name}
                      >
                        {w.effective_thac0 - atk.hit_bonus + (rangeModifiers[idx] || 0)}
                      </button>
                    {:else}
                      <span class="text-ink-faint">&mdash;</span>
                    {/if}
                  </td>
                {/each}

                <!-- Item attack THAC0 sub-columns -->
                {#each itemAttackNames as atkName}
                  {@const iatk = getItemAttack(w, atkName)}
                  <td class="text-center py-1">
                    {#if iatk}
                      <button
                        class="font-serif text-lg cursor-pointer hover:bg-parchment-100 transition-colors rounded px-1.5 -mx-1"
                        disabled={!rollDice}
                        on:click={() => rollItemAttack(w, idx, iatk)}
                        title={iatk.name}
                      >
                        {w.effective_thac0 - (iatk.hit_bonus || 0) + (rangeModifiers[idx] || 0)}
                      </button>
                    {:else}
                      <span class="text-ink-faint">&mdash;</span>
                    {/if}
                  </td>
                {/each}

                <!-- Normal Damage -->
                <td class="text-center py-1">
                  <button
                    class="cursor-pointer hover:bg-parchment-100 transition-colors rounded px-1.5 -mx-1"
                    disabled={!rollDice}
                    on:click={() => {
                      rollDice && rollDice(w.damage_dice, (total) => {
                        const dmg = total + (w.damage_mod || 0);
                        const modStr = w.damage_mod
                          ? ` (${total} ${w.damage_mod > 0 ? '+' : '\u2212'} ${Math.abs(w.damage_mod)})`
                          : '';
                        return `${dmg} damage${modStr}`;
                      });
                    }}
                  >
                    {w.damage_dice}{#if w.damage_mod > 0}+{w.damage_mod}{:else if w.damage_mod < 0}{w.damage_mod}{/if}
                  </button>
                </td>

                <!-- Class attack Damage sub-columns -->
                {#each classAttackNames as atkName}
                  {@const atk = getClassAttack(w, atkName)}
                  <td class="text-center py-1">
                    {#if atk}
                      <button
                        class="cursor-pointer hover:bg-parchment-100 transition-colors rounded px-1.5 -mx-1"
                        disabled={!rollDice}
                        on:click={() => rollDamageWithAction(w, atk)}
                        title={atk.condition || atk.name}
                      >
                        <span>{w.damage_dice}{#if w.damage_mod > 0}+{w.damage_mod}{:else if w.damage_mod < 0}{w.damage_mod}{/if}</span>
                        {#if atk.damage_multiplier}
                          <span class="text-ink-faint"> ×{atk.damage_multiplier}</span>
                        {/if}
                      </button>
                      {#if atk.effect}
                        <div class="text-[10px] text-ink-faint leading-tight">
                          {atk.effect}{#if atk.effect_penalty != null && atk.effect_penalty !== 0} ({atk.effect_penalty}){/if}
                        </div>
                      {/if}
                    {:else}
                      <span class="text-ink-faint">&mdash;</span>
                    {/if}
                  </td>
                {/each}

                <!-- Item attack Damage sub-columns -->
                {#each itemAttackNames as atkName}
                  {@const iatk = getItemAttack(w, atkName)}
                  <td class="text-center py-1">
                    {#if iatk}
                      <button
                        class="cursor-pointer hover:bg-parchment-100 transition-colors rounded px-1.5 -mx-1"
                        disabled={!rollDice}
                        on:click={() => rollItemDamage(w, iatk)}
                        title={iatk.name}
                      >
                        <span>{w.damage_dice}{#if w.damage_mod > 0}+{w.damage_mod}{:else if w.damage_mod < 0}{w.damage_mod}{/if}</span>
                        {#if iatk.damage_bonus}
                          <span class="text-ink-faint"> +{iatk.damage_bonus}</span>
                        {/if}
                      </button>
                    {:else}
                      <span class="text-ink-faint">&mdash;</span>
                    {/if}
                  </td>
                {/each}

                <!-- Weapon quality Damage sub-columns (Brace, Charge) -->
                {#each qualityDamageNames as qName}
                  {@const qAction = getQualityDamageAction(w, qName)}
                  <td class="text-center py-1">
                    {#if qAction}
                      <button
                        class="cursor-pointer hover:bg-parchment-100 transition-colors rounded px-1.5 -mx-1"
                        disabled={!rollDice}
                        on:click={() => rollDamageWithAction(w, qAction)}
                        title={qAction.condition}
                      >
                        <span>{w.damage_dice}{#if w.damage_mod > 0}+{w.damage_mod}{:else if w.damage_mod < 0}{w.damage_mod}{/if}</span>
                        <span class="text-ink-faint"> ×{qAction.damage_multiplier}</span>
                      </button>
                    {:else}
                      <span class="text-ink-faint">&mdash;</span>
                    {/if}
                  </td>
                {/each}
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  {/if}


</div>

<!-- Warning Toast -->
{#if warningToast}
  <button
    class="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 shadow-lg rounded-sm p-4
           cursor-pointer print:hidden min-w-[200px] text-center
           border border-red-900/30 bg-red-50"
    on:click={() => { warningToast = ''; }}
  >
    <div class="text-sm text-red-800 font-medium">{warningToast}</div>
  </button>
{/if}

<style>
  .hp-btn {
    width: 2.5rem;
    height: 2.5rem;
    border-radius: 9999px;
    border: 1.5px solid;
    font-size: 1.25rem;
    font-weight: 600;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: background-color 0.15s;
  }
  .hp-btn:disabled {
    opacity: 0.3;
    cursor: default;
  }
  .hover-highlight:hover {
    background-color: rgb(var(--color-parchment-100));
  }
  .range-toggle {
    font-size: 0.7rem;
    padding: 0.1rem 0.35rem;
    border-radius: 0.2rem;
    cursor: pointer;
    transition: background-color 0.15s;
    color: rgb(var(--color-ink-faint));
  }
  .range-toggle:hover {
    background-color: rgb(var(--color-parchment-100));
  }
  .range-active {
    background-color: rgb(var(--color-parchment-200));
    font-weight: 600;
    color: rgb(var(--color-ink));
  }
</style>
