<script>
  import { ITEM_METADATA_TEMPLATES, METADATA_FIELD_REFERENCE } from '$lib/item-metadata.js';

  /** Initial item data for edit mode (null for create) */
  export let initialData = null;
  /** Called with the assembled payload */
  export let onSubmit;

  const ITEM_TYPES = [
    'weapon', 'armor', 'ammo',
    'potion', 'scroll', 'ring', 'wand', 'wondrous',
    'consumable', 'tool', 'treasure',
  ];

  // --- Individual form fields (Svelte 5 reactivity safety) ---
  let name = initialData?.name || '';
  let unidentifiedName = initialData?.unidentified_name || '';
  let itemType = initialData?.item_type || 'weapon';
  let equippable = initialData?.equippable || false;
  let gmOnly = initialData?.gm_only || false;
  let fillable = initialData?.item_metadata?.fillable || false;
  let capacity = initialData?.item_metadata?.capacity != null ? String(initialData.item_metadata.capacity) : '';
  let weight = initialData?.weight != null ? String(initialData.weight) : '';
  let costGp = initialData?.cost_gp != null ? String(initialData.cost_gp) : '';
  let descriptionPlayer = initialData?.description_player || '';
  let descriptionGm = initialData?.description_gm || '';
  let metadataJson = initialData?.item_metadata
    ? JSON.stringify(initialData.item_metadata, null, 2)
    : formatTemplate(itemType);

  // Secrets — independent array of {text, revealed} objects
  let secretEntries = (initialData?.secrets || []).map(s => ({ text: s.text, revealed: s.revealed }));

  // --- Item Abilities (ability_metadata) ---
  const ABILITY_TYPES = ['modifier', 'skill', 'round_effect', 'special_attack', 'aura'];
  const ABILITY_TYPE_LABELS = {
    modifier: 'Modifier',
    skill: 'Skill',
    round_effect: 'Round Effect',
    special_attack: 'Special Attack',
    aura: 'Aura',
  };
  const MODIFIER_TARGETS = [
    'strength', 'dexterity', 'wisdom', 'intelligence', 'constitution', 'charisma',
    'ac', 'missile_thac0', 'melee_thac0', 'movement_rate',
  ];
  const MODIFIER_TARGET_LABELS = {
    strength: 'STR', dexterity: 'DEX', wisdom: 'WIS', intelligence: 'INT',
    constitution: 'CON', charisma: 'CHA', ac: 'AC',
    missile_thac0: 'Missile THAC0', melee_thac0: 'Melee THAC0', movement_rate: 'Movement',
  };

  // Parse existing ability_metadata from initialData, then remove from JSON textarea
  function initAbilities() {
    const meta = initialData?.item_metadata;
    if (!meta || !Array.isArray(meta.ability_metadata)) return [];
    return meta.ability_metadata.map(a => ({ ...a }));
  }

  let abilityEntries = initAbilities();

  // Strip fields owned by structured editors from metadataJson on init
  {
    let needsClean = abilityEntries.length > 0 || fillable || capacity;
    if (needsClean && metadataJson.trim()) {
      try {
        const parsed = JSON.parse(metadataJson);
        delete parsed.ability_metadata;
        delete parsed.fillable;
        delete parsed.capacity;
        metadataJson = Object.keys(parsed).length > 0 ? JSON.stringify(parsed, null, 2) : '';
      } catch { /* leave as-is */ }
    }
  }

  function addAbility() {
    abilityEntries = [...abilityEntries, { type: 'modifier', target: 'ac', value: 0 }];
  }

  function removeAbility(index) {
    abilityEntries = abilityEntries.filter((_, i) => i !== index);
  }

  function onAbilityTypeChange(index) {
    const entry = abilityEntries[index];
    // Reset to type defaults
    if (entry.type === 'modifier') {
      abilityEntries[index] = { type: 'modifier', target: 'ac', value: 0 };
    } else if (entry.type === 'skill') {
      abilityEntries[index] = { type: 'skill', rolls: {} };
    } else if (entry.type === 'round_effect') {
      abilityEntries[index] = { type: 'round_effect', effect: 'hp', value: 1, description: '' };
    } else if (entry.type === 'special_attack') {
      abilityEntries[index] = { type: 'special_attack', attacks: [] };
    } else if (entry.type === 'aura') {
      abilityEntries[index] = { type: 'aura', description: '' };
    }
    abilityEntries = abilityEntries;
  }

  // Skill roll helpers
  function addSkillRoll(abilityIndex) {
    const entry = abilityEntries[abilityIndex];
    if (!entry.rolls) entry.rolls = {};
    entry.rolls[`Skill ${Object.keys(entry.rolls).length + 1}`] = { chance: 50, die: 100 };
    abilityEntries = abilityEntries;
  }

  function removeSkillRoll(abilityIndex, rollName) {
    delete abilityEntries[abilityIndex].rolls[rollName];
    abilityEntries = abilityEntries;
  }

  function renameSkillRoll(abilityIndex, oldName, newName) {
    const rolls = abilityEntries[abilityIndex].rolls;
    if (oldName === newName || !newName.trim()) return;
    rolls[newName.trim()] = rolls[oldName];
    delete rolls[oldName];
    abilityEntries = abilityEntries;
  }

  // Special attack helpers
  function addSpecialAttack(abilityIndex) {
    if (!abilityEntries[abilityIndex].attacks) abilityEntries[abilityIndex].attacks = [];
    abilityEntries[abilityIndex].attacks = [
      ...abilityEntries[abilityIndex].attacks,
      { name: '', hit_bonus: 0, damage_bonus: 0 },
    ];
    abilityEntries = abilityEntries;
  }

  function removeSpecialAttack(abilityIndex, attackIndex) {
    abilityEntries[abilityIndex].attacks = abilityEntries[abilityIndex].attacks.filter((_, i) => i !== attackIndex);
    abilityEntries = abilityEntries;
  }

  /** Format a template as pretty JSON, or empty string for empty objects */
  function formatTemplate(type) {
    const tmpl = ITEM_METADATA_TEMPLATES[type];
    if (!tmpl || Object.keys(tmpl).length === 0) return '';
    return JSON.stringify(tmpl, null, 2);
  }

  function onTypeChange() {
    // Only auto-populate if metadata is empty or matches a known template
    const trimmed = metadataJson.trim();
    const isTemplate = !trimmed || ITEM_TYPES.some(
      (t) => trimmed === JSON.stringify(ITEM_METADATA_TEMPLATES[t], null, 2)
    );
    if (isTemplate) {
      metadataJson = formatTemplate(itemType);
      equippable = ['weapon', 'armor', 'ammo'].includes(itemType);
    }
  }

  function addSecret() {
    secretEntries = [...secretEntries, { text: '', revealed: false }];
  }

  function removeSecret(index) {
    secretEntries = secretEntries.filter((_, i) => i !== index);
  }

  let submitting = false;
  let error = '';

  async function handleSubmit() {
    if (!name.trim()) { error = 'Item name is required.'; return; }

    // Validate JSON if provided
    let parsedMeta = null;
    if (metadataJson.trim()) {
      try {
        parsedMeta = JSON.parse(metadataJson.trim());
      } catch (e) {
        error = 'Item Metadata is not valid JSON.';
        return;
      }
    }

    submitting = true;
    error = '';

    try {
      const cleanedSecrets = secretEntries
        .filter(s => s.text.trim())
        .map(s => ({ text: s.text.trim(), revealed: s.revealed }));

      // Merge structured fields into item_metadata
      let finalMeta = parsedMeta ? { ...parsedMeta } : {};
      if (abilityEntries.length > 0) {
        finalMeta.ability_metadata = abilityEntries;
      } else {
        delete finalMeta.ability_metadata;
      }
      if (fillable) {
        finalMeta.fillable = true;
      } else {
        delete finalMeta.fillable;
      }
      if (capacity && parseFloat(capacity) > 0) {
        finalMeta.capacity = parseFloat(capacity);
      } else {
        delete finalMeta.capacity;
      }
      // If finalMeta is empty, set to null
      if (Object.keys(finalMeta).length === 0) finalMeta = null;

      const payload = {
        name: name.trim(),
        unidentified_name: unidentifiedName.trim() || null,
        item_type: itemType,
        equippable,
        gm_only: gmOnly,
        weight: weight !== '' && weight != null ? parseFloat(weight) : null,
        cost_gp: costGp !== '' && costGp != null ? parseFloat(costGp) : null,
        description_player: descriptionPlayer.trim() || null,
        description_gm: descriptionGm.trim() || null,
        secrets: cleanedSecrets.length > 0 ? cleanedSecrets : null,
        item_metadata: finalMeta,
      };

      await onSubmit(payload);
    } catch (e) {
      error = e.message;
      submitting = false;
    }
  }
</script>

<div class="flex flex-col gap-4">
  <div class="panel flex flex-col gap-4">
    <div>
      <label class="block text-sm text-ink mb-1" for="item-name">Name</label>
      <input id="item-name" class="input w-full" type="text" bind:value={name} placeholder="Sword +1" />
    </div>

    <div>
      <label class="block text-sm text-ink mb-1" for="item-unid-name">
        Unidentified Name <span class="text-ink-faint">(leave blank for mundane items)</span>
      </label>
      <input id="item-unid-name" class="input w-full" type="text" bind:value={unidentifiedName} placeholder="Sword, Long" />
    </div>

    <div class="grid grid-cols-2 gap-4">
      <div>
        <label class="block text-sm text-ink mb-1" for="item-type">Item Type</label>
        <select id="item-type" class="input w-full" bind:value={itemType} on:change={onTypeChange}>
          {#each ITEM_TYPES as t}
            <option value={t}>{t}</option>
          {/each}
        </select>
      </div>
      <div class="flex items-end gap-4 pb-2">
        <label class="flex items-center gap-2 text-sm text-ink cursor-pointer">
          <input type="checkbox" bind:checked={equippable} class="accent-ink" />
          Equippable
        </label>
        <label class="flex items-center gap-2 text-sm text-ink cursor-pointer" title="Can hold liquids (waterskin, flask)">
          <input type="checkbox" bind:checked={fillable} class="accent-ink" />
          Fillable
        </label>
        <label class="flex items-center gap-2 text-sm text-ink cursor-pointer" title="Hidden from player 'Add Item' — only assignable by GM">
          <input type="checkbox" bind:checked={gmOnly} class="accent-ink" />
          GM Only
        </label>
      </div>
    </div>

    <div class="grid grid-cols-3 gap-4">
      <div>
        <label class="block text-sm text-ink mb-1" for="item-weight">Weight <span class="text-ink-faint">(coins)</span></label>
        <input id="item-weight" class="input w-full" type="number" step="any" bind:value={weight} placeholder="10" />
      </div>
      <div>
        <label class="block text-sm text-ink mb-1" for="item-cost">Cost <span class="text-ink-faint">(GP)</span></label>
        <input id="item-cost" class="input w-full" type="number" step="any" bind:value={costGp} placeholder="25" />
      </div>
      <div>
        <label class="block text-sm text-ink mb-1" for="item-capacity">Capacity <span class="text-ink-faint">(coins)</span></label>
        <input id="item-capacity" class="input w-full" type="number" bind:value={capacity} placeholder="400" />
        <p class="text-xs text-ink-faint mt-0.5">Container capacity (backpacks, sacks)</p>
      </div>
    </div>

    <div>
      <label class="block text-sm text-ink mb-1" for="item-desc-player">Player Description <span class="text-ink-faint">(supports markdown)</span></label>
      <textarea id="item-desc-player" class="input w-full resize-none" rows="4" bind:value={descriptionPlayer} placeholder="What players can see..."></textarea>
    </div>

    <div>
      <label class="block text-sm text-ink mb-1" for="item-desc-gm">GM Description <span class="text-ink-faint">(supports markdown)</span></label>
      <textarea id="item-desc-gm" class="input w-full resize-none" rows="4" bind:value={descriptionGm} placeholder="Secret GM notes..."></textarea>
    </div>

    <!-- Revealable Secrets -->
    <div>
      <div class="flex items-center justify-between mb-1">
        <label class="block text-sm text-ink">Secrets <span class="text-ink-faint">(revealable to players)</span></label>
        <button type="button" class="btn-ghost text-xs" on:click={addSecret}>+ Add Secret</button>
      </div>
      {#if secretEntries.length > 0}
        <div class="space-y-2">
          {#each secretEntries as entry, i}
            <div class="flex gap-2 items-start border border-parchment-200 rounded p-2">
              <textarea
                class="input flex-1 resize-none text-sm"
                rows="2"
                placeholder="Secret text (e.g. 'This sword is +1')"
                bind:value={entry.text}
              ></textarea>
              <div class="flex flex-col items-center gap-1 shrink-0">
                <label class="flex items-center gap-1 text-xs text-ink-faint cursor-pointer" title="Revealed to players">
                  <input type="checkbox" bind:checked={entry.revealed} class="accent-ink" />
                  Shown
                </label>
                <button type="button" class="btn-danger text-xs px-1.5 py-0.5" on:click={() => removeSecret(i)}>Remove</button>
              </div>
            </div>
          {/each}
        </div>
      {:else}
        <p class="text-xs text-ink-faint">No secrets. Click "+ Add Secret" to add one.</p>
      {/if}
    </div>

    <!-- Item Abilities (ability_metadata) -->
    <div>
      <div class="flex items-center justify-between mb-1">
        <label class="block text-sm text-ink">Item Abilities <span class="text-ink-faint">(modifier, skill, aura, etc.)</span></label>
        <button type="button" class="btn-ghost text-xs" on:click={addAbility}>+ Add Ability</button>
      </div>
      {#if abilityEntries.length > 0}
        <div class="space-y-3">
          {#each abilityEntries as entry, i}
            <div class="border border-parchment-200 rounded p-3 space-y-2">
              <div class="flex items-center gap-2">
                <select class="input text-sm flex-1" bind:value={entry.type} on:change={() => onAbilityTypeChange(i)}>
                  {#each ABILITY_TYPES as t}
                    <option value={t}>{ABILITY_TYPE_LABELS[t]}</option>
                  {/each}
                </select>
                <button type="button" class="btn-danger text-xs px-1.5 py-0.5" on:click={() => removeAbility(i)}>Remove</button>
              </div>

              {#if entry.type === 'modifier'}
                <div class="grid grid-cols-3 gap-2">
                  <div>
                    <label class="text-xs text-ink-faint">Target</label>
                    <select class="input w-full text-sm" bind:value={entry.target}>
                      {#each MODIFIER_TARGETS as t}
                        <option value={t}>{MODIFIER_TARGET_LABELS[t]}</option>
                      {/each}
                    </select>
                  </div>
                  <div>
                    <label class="text-xs text-ink-faint">Value</label>
                    <input class="input w-full text-sm" type="number" bind:value={entry.value} />
                  </div>
                  <div>
                    <label class="text-xs text-ink-faint">Condition <span class="text-ink-faint">(opt.)</span></label>
                    <input class="input w-full text-sm" type="text" bind:value={entry.condition} placeholder="e.g. DEX 7-13" />
                  </div>
                </div>

              {:else if entry.type === 'skill'}
                <div class="space-y-2">
                  {#each Object.entries(entry.rolls || {}) as [rollName, roll]}
                    <div class="flex gap-2 items-end">
                      <div class="flex-1">
                        <label class="text-xs text-ink-faint">Name</label>
                        <input class="input w-full text-sm" type="text" value={rollName}
                          on:blur={(e) => renameSkillRoll(i, rollName, e.target.value)} />
                      </div>
                      <div class="w-20">
                        <label class="text-xs text-ink-faint">Chance</label>
                        <input class="input w-full text-sm" type="number" bind:value={roll.chance} />
                      </div>
                      <div class="w-20">
                        <label class="text-xs text-ink-faint">Die</label>
                        <select class="input w-full text-sm" bind:value={roll.die}>
                          <option value={6}>d6</option>
                          <option value={100}>d100</option>
                        </select>
                      </div>
                      <button type="button" class="btn-danger text-xs px-1.5 py-0.5" on:click={() => removeSkillRoll(i, rollName)}>X</button>
                    </div>
                  {/each}
                  <button type="button" class="btn-ghost text-xs" on:click={() => addSkillRoll(i)}>+ Add Skill Roll</button>
                </div>

              {:else if entry.type === 'round_effect'}
                <div class="grid grid-cols-3 gap-2">
                  <div>
                    <label class="text-xs text-ink-faint">Effect</label>
                    <select class="input w-full text-sm" bind:value={entry.effect}>
                      <option value="hp">HP</option>
                    </select>
                  </div>
                  <div>
                    <label class="text-xs text-ink-faint">Value</label>
                    <input class="input w-full text-sm" type="number" bind:value={entry.value} />
                  </div>
                  <div>
                    <label class="text-xs text-ink-faint">Description</label>
                    <input class="input w-full text-sm" type="text" bind:value={entry.description} placeholder="Regenerate 1 HP/round" />
                  </div>
                </div>

              {:else if entry.type === 'special_attack'}
                <div class="space-y-2">
                  {#each (entry.attacks || []) as atk, ai}
                    <div class="flex gap-2 items-end">
                      <div class="flex-1">
                        <label class="text-xs text-ink-faint">Name</label>
                        <input class="input w-full text-sm" type="text" bind:value={atk.name} placeholder="vs Undead" />
                      </div>
                      <div class="w-20">
                        <label class="text-xs text-ink-faint">Hit+</label>
                        <input class="input w-full text-sm" type="number" bind:value={atk.hit_bonus} />
                      </div>
                      <div class="w-20">
                        <label class="text-xs text-ink-faint">Dmg+</label>
                        <input class="input w-full text-sm" type="number" bind:value={atk.damage_bonus} />
                      </div>
                      <button type="button" class="btn-danger text-xs px-1.5 py-0.5" on:click={() => removeSpecialAttack(i, ai)}>X</button>
                    </div>
                  {/each}
                  <button type="button" class="btn-ghost text-xs" on:click={() => addSpecialAttack(i)}>+ Add Attack</button>
                </div>

              {:else if entry.type === 'aura'}
                <div>
                  <label class="text-xs text-ink-faint">Description</label>
                  <textarea class="input w-full resize-none text-sm" rows="2" bind:value={entry.description} placeholder="Casts light in 30' radius"></textarea>
                </div>
              {/if}
            </div>
          {/each}
        </div>
      {:else}
        <p class="text-xs text-ink-faint">No item abilities. Click "+ Add Ability" to add modifiers, skills, or effects.</p>
      {/if}
    </div>

    <div>
      <label class="block text-sm text-ink mb-1" for="item-metadata">Item Metadata <span class="text-ink-faint">(JSON — damage_dice, ac, range, etc.)</span></label>
      <textarea id="item-metadata" class="input w-full resize-none font-mono text-sm" rows="5" bind:value={metadataJson} placeholder={'{"damage_dice": "1d8", "weapon_type": "melee"}'}></textarea>
      {#if METADATA_FIELD_REFERENCE[itemType]?.length}
        <details class="mt-1">
          <summary class="text-xs text-ink-faint cursor-pointer hover:text-ink">
            Available fields for <strong>{itemType}</strong>
          </summary>
          <div class="mt-1 bg-parchment-100 rounded p-2 text-xs font-mono space-y-0.5">
            {#each METADATA_FIELD_REFERENCE[itemType] as field}
              <div>
                <span class="text-ink font-medium">{field.key}</span>
                <span class="text-ink-faint ml-1">({field.type})</span>
                <span class="text-ink-faint ml-1">— {field.desc}</span>
              </div>
            {/each}
          </div>
        </details>
      {/if}
    </div>
  </div>

  {#if error}
    <p class="text-red-700 text-sm">{error}</p>
  {/if}

  <div class="flex gap-3">
    <button class="btn" on:click={handleSubmit} disabled={submitting}>
      {submitting ? 'Saving...' : 'Save Item'}
    </button>
    <a href="/items" class="btn-ghost">Cancel</a>
  </div>
</div>
