<script>
  /**
   * Dynamic key-value editor for the abilities dict + ability_metadata.
   * Converts object {name: description} to [{name, description, metaType, ...}] for editing.
   * @prop abilities - object {name: description}
   * @prop abilityMetadata - object {name: {type, target?, values?, rolls?, attacks?}}
   * @prop maxLevel - current max level for sizing arrays
   *
   * Call getAbilities() to read the current state as an object.
   * Call getAbilityMetadata() to read metadata as an object.
   * Call resizeToLevel(n) when max level changes.
   */
  export let abilities = {};
  export let abilityMetadata = {};
  export let maxLevel = 14;

  const META_TYPES = [
    { value: 'none', label: 'None' },
    { value: 'modifier', label: 'Modifier' },
    { value: 'skill', label: 'Skill (Rollable)' },
    { value: 'special_attack', label: 'Special Attack' },
  ];

  const MODIFIER_TARGETS = [
    { value: 'ac', label: 'AC' },
    { value: 'missile_thac0', label: 'Missile THAC0' },
    { value: 'melee_thac0', label: 'Melee THAC0' },
  ];

  const WEAPON_TYPES = [
    { value: 'melee', label: 'Melee' },
    { value: 'ranged', label: 'Ranged' },
    { value: 'thrown', label: 'Thrown' },
  ];

  function fill(n, v) { return Array(n).fill(v); }

  function padArr(arr, len, defaultVal) {
    if (!arr) return fill(len, defaultVal);
    if (arr.length >= len) return arr.slice(0, len);
    return [...arr, ...fill(len - arr.length, defaultVal)];
  }

  function makeDefaultAttack() {
    return {
      name: '',
      hit_bonus: 0,
      damage_multiplier: null,
      applies_to: ['melee'],
      condition: '',
      effect: '',
      effect_penalty: null,
      useLevelPenalty: false,
      levelPenalties: fill(maxLevel, 0),
    };
  }

  function parseAttack(atk) {
    const hasLevelPenalty = Array.isArray(atk.effect_penalty);
    return {
      name: atk.name || '',
      hit_bonus: atk.hit_bonus || 0,
      damage_multiplier: atk.damage_multiplier ?? null,
      applies_to: atk.applies_to || ['melee'],
      condition: atk.condition || '',
      effect: atk.effect || '',
      effect_penalty: hasLevelPenalty ? null : (atk.effect_penalty ?? null),
      useLevelPenalty: hasLevelPenalty,
      levelPenalties: hasLevelPenalty ? padArr(atk.effect_penalty, maxLevel, 0) : fill(maxLevel, 0),
    };
  }

  // Build entry from ability name + description + optional metadata
  function buildEntry(name, description) {
    const meta = abilityMetadata[name];
    const base = { name, description, modTarget: 'ac', modValues: fill(maxLevel, 0), rolls: [], attacks: [] };
    if (!meta) {
      return { ...base, metaType: 'none' };
    }
    if (meta.type === 'modifier') {
      return {
        ...base, metaType: 'modifier',
        modTarget: meta.target || 'ac',
        modValues: padArr(meta.values, maxLevel, 0),
      };
    }
    if (meta.type === 'skill') {
      const rolls = Object.entries(meta.rolls || {}).map(([rName, r]) => ({
        name: rName, chance: r.chance, die: r.die || 6,
      }));
      return {
        ...base, metaType: 'skill',
        rolls: rolls.length > 0 ? rolls : [{ name: '', chance: 1, die: 6 }],
      };
    }
    if (meta.type === 'special_attack') {
      const attacks = (meta.attacks || []).map(parseAttack);
      return {
        ...base, metaType: 'special_attack',
        attacks: attacks.length > 0 ? attacks : [makeDefaultAttack()],
      };
    }
    return { ...base, metaType: 'none' };
  }

  // Convert object to editable array
  let entries = Object.entries(abilities).map(([name, description]) => buildEntry(name, description));

  /** Return current entries as {name: description} object. */
  export function getAbilities() {
    const obj = {};
    for (const e of entries) {
      if (e.name.trim()) obj[e.name.trim()] = e.description;
    }
    return obj;
  }

  /** Return current metadata as {name: {type, ...}} object. */
  export function getAbilityMetadata() {
    const obj = {};
    for (const e of entries) {
      const key = e.name.trim();
      if (!key) continue;
      if (e.metaType === 'modifier') {
        obj[key] = {
          type: 'modifier',
          target: e.modTarget,
          values: [...e.modValues],
        };
      } else if (e.metaType === 'skill') {
        const rolls = {};
        for (const r of e.rolls) {
          if (r.name.trim()) {
            rolls[r.name.trim()] = { chance: r.chance, die: r.die };
          }
        }
        if (Object.keys(rolls).length > 0) {
          obj[key] = { type: 'skill', rolls };
        }
      } else if (e.metaType === 'special_attack') {
        const attacks = [];
        for (const a of e.attacks) {
          if (!a.name.trim()) continue;
          const atk = {
            name: a.name.trim(),
            hit_bonus: a.hit_bonus || 0,
            applies_to: a.applies_to,
            condition: a.condition || undefined,
          };
          if (a.damage_multiplier != null && a.damage_multiplier > 0) {
            atk.damage_multiplier = a.damage_multiplier;
          }
          if (a.effect) {
            atk.effect = a.effect;
          }
          if (a.useLevelPenalty) {
            atk.effect_penalty = [...a.levelPenalties];
          }
          attacks.push(atk);
        }
        if (attacks.length > 0) {
          obj[key] = { type: 'special_attack', attacks };
        }
      }
      // 'none' → no metadata entry
    }
    return obj;
  }

  /** Resize level-indexed arrays when max level changes. */
  export function resizeToLevel(newMax) {
    maxLevel = newMax;
    for (const e of entries) {
      e.modValues = padArr(e.modValues, newMax, 0);
      for (const a of e.attacks) {
        if (a.useLevelPenalty) {
          a.levelPenalties = padArr(a.levelPenalties, newMax, 0);
        }
      }
    }
    entries = entries; // trigger reactivity
  }

  function addEntry() {
    entries = [...entries, {
      name: '', description: '', metaType: 'none',
      modTarget: 'ac', modValues: fill(maxLevel, 0),
      rolls: [], attacks: [],
    }];
  }

  function removeEntry(index) {
    entries = entries.filter((_, i) => i !== index);
  }

  function addRoll(entry) {
    entry.rolls = [...entry.rolls, { name: '', chance: 1, die: 6 }];
    entries = entries; // trigger reactivity
  }

  function removeRoll(entry, ri) {
    entry.rolls = entry.rolls.filter((_, i) => i !== ri);
    entries = entries;
  }

  function addAttack(entry) {
    entry.attacks = [...entry.attacks, makeDefaultAttack()];
    entries = entries;
  }

  function removeAttack(entry, ai) {
    entry.attacks = entry.attacks.filter((_, i) => i !== ai);
    entries = entries;
  }

  function toggleAppliesTo(atk, wType) {
    if (atk.applies_to.includes(wType)) {
      atk.applies_to = atk.applies_to.filter(t => t !== wType);
    } else {
      atk.applies_to = [...atk.applies_to, wType];
    }
    entries = entries;
  }
</script>

<div class="flex flex-col gap-3">
  {#each entries as entry, i}
    <div class="panel flex flex-col gap-2 p-3">
      <div class="flex items-center gap-2">
        <input
          type="text"
          class="input flex-1"
          placeholder="Ability name"
          bind:value={entry.name}
        />
        <select class="input w-40" bind:value={entry.metaType}>
          {#each META_TYPES as mt}
            <option value={mt.value}>{mt.label}</option>
          {/each}
        </select>
        <button
          type="button"
          class="btn-danger text-xs px-2 py-0.5"
          on:click={() => removeEntry(i)}
        >
          Remove
        </button>
      </div>
      <textarea
        class="input w-full resize-none text-sm"
        rows="2"
        placeholder="Description..."
        bind:value={entry.description}
      ></textarea>

      <!-- Modifier fields -->
      {#if entry.metaType === 'modifier'}
        <div class="border border-parchment-300 rounded p-2 bg-parchment-50">
          <div class="flex items-center gap-2 mb-2">
            <span class="text-xs text-ink-faint">Target:</span>
            <select class="input w-24 text-sm" bind:value={entry.modTarget}>
              {#each MODIFIER_TARGETS as t}
                <option value={t.value}>{t.label}</option>
              {/each}
            </select>
          </div>
          <span class="text-xs text-ink-faint block mb-1">Values by level (negative = better for AC):</span>
          <div class="flex flex-wrap gap-1">
            {#each entry.modValues as _, li}
              <div class="flex flex-col items-center">
                <span class="text-[10px] text-ink-faint">L{li + 1}</span>
                <input
                  type="number"
                  class="input w-12 text-center text-sm p-0.5"
                  bind:value={entry.modValues[li]}
                />
              </div>
            {/each}
          </div>
        </div>
      {/if}

      <!-- Skill fields -->
      {#if entry.metaType === 'skill'}
        <div class="border border-parchment-300 rounded p-2 bg-parchment-50">
          <span class="text-xs text-ink-faint block mb-1">Rollable skills:</span>
          {#each entry.rolls as roll, ri}
            <div class="flex items-center gap-2 mb-1">
              <input
                type="text"
                class="input flex-1 text-sm"
                placeholder="Roll name (e.g. Foraging)"
                bind:value={roll.name}
              />
              <input
                type="number"
                class="input w-14 text-center text-sm"
                min="1"
                bind:value={roll.chance}
              />
              <span class="text-sm text-ink-faint">in</span>
              <select class="input w-16 text-sm" bind:value={roll.die}>
                <option value={6}>d6</option>
                <option value={100}>d100</option>
              </select>
              <button
                type="button"
                class="btn-danger text-xs px-1 py-0.5"
                on:click={() => removeRoll(entry, ri)}
              >x</button>
            </div>
          {/each}
          <button type="button" class="btn-ghost text-xs mt-1" on:click={() => addRoll(entry)}>
            + Add Roll
          </button>
        </div>
      {/if}

      <!-- Special Attack fields -->
      {#if entry.metaType === 'special_attack'}
        <div class="border border-parchment-300 rounded p-2 bg-parchment-50">
          <span class="text-xs text-ink-faint block mb-1">Weapon special attacks:</span>
          {#each entry.attacks as atk, ai}
            <div class="border border-parchment-200 rounded p-2 mb-2 bg-parchment-100/50">
              <div class="flex items-center gap-2 mb-1.5">
                <input
                  type="text"
                  class="input flex-1 text-sm"
                  placeholder="Attack name (e.g. Backstab)"
                  bind:value={atk.name}
                />
                <button
                  type="button"
                  class="btn-danger text-xs px-1 py-0.5"
                  on:click={() => removeAttack(entry, ai)}
                >x</button>
              </div>
              <div class="grid grid-cols-2 gap-2 text-sm mb-1.5">
                <div class="flex items-center gap-1">
                  <span class="text-xs text-ink-faint whitespace-nowrap">Hit bonus:</span>
                  <input
                    type="number"
                    class="input w-16 text-center text-sm"
                    bind:value={atk.hit_bonus}
                  />
                </div>
                <div class="flex items-center gap-1">
                  <span class="text-xs text-ink-faint whitespace-nowrap">Dmg multiplier:</span>
                  <input
                    type="number"
                    class="input w-16 text-center text-sm"
                    min="0"
                    placeholder="—"
                    bind:value={atk.damage_multiplier}
                  />
                </div>
              </div>
              <div class="flex items-center gap-2 mb-1.5">
                <span class="text-xs text-ink-faint">Applies to:</span>
                {#each WEAPON_TYPES as wt}
                  <label class="flex items-center gap-1 text-xs text-ink">
                    <input
                      type="checkbox"
                      checked={atk.applies_to.includes(wt.value)}
                      on:change={() => toggleAppliesTo(atk, wt.value)}
                    />
                    {wt.label}
                  </label>
                {/each}
              </div>
              <div class="flex items-center gap-2 mb-1.5">
                <span class="text-xs text-ink-faint">Condition:</span>
                <input
                  type="text"
                  class="input flex-1 text-sm"
                  placeholder="e.g. Opponent unaware"
                  bind:value={atk.condition}
                />
              </div>
              <div class="flex items-center gap-2 mb-1.5">
                <span class="text-xs text-ink-faint">Effect:</span>
                <input
                  type="text"
                  class="input flex-1 text-sm"
                  placeholder="e.g. Save vs Death"
                  bind:value={atk.effect}
                />
              </div>
              {#if atk.effect}
                <label class="flex items-center gap-1 text-xs text-ink mb-1">
                  <input type="checkbox" bind:checked={atk.useLevelPenalty} />
                  Level-scaling save penalty
                </label>
                {#if atk.useLevelPenalty}
                  <div class="flex flex-wrap gap-1">
                    {#each atk.levelPenalties as _, li}
                      <div class="flex flex-col items-center">
                        <span class="text-[10px] text-ink-faint">L{li + 1}</span>
                        <input
                          type="number"
                          class="input w-12 text-center text-sm p-0.5"
                          bind:value={atk.levelPenalties[li]}
                        />
                      </div>
                    {/each}
                  </div>
                {/if}
              {/if}
            </div>
          {/each}
          <button type="button" class="btn-ghost text-xs mt-1" on:click={() => addAttack(entry)}>
            + Add Attack
          </button>
        </div>
      {/if}
    </div>
  {/each}

  <button type="button" class="btn-ghost text-sm self-start" on:click={addEntry}>
    + Add Ability
  </button>
</div>
