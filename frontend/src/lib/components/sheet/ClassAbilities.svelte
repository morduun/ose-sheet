<script>
  import Markdown from '$lib/components/shared/Markdown.svelte';

  export let character;

  $: classData = character.character_class?.class_data ?? {};
  $: levelIndex = Math.max(0, (character.level ?? 1) - 1);

  // --- Abilities (dict: name → description) ---
  $: abilitiesEntries = classData.abilities
    ? Object.entries(classData.abilities)
    : [];
  $: hasAbilities = abilitiesEntries.length > 0;

  // --- Ability Metadata (for modifier badges) ---
  $: abilityMeta = classData.ability_metadata ?? {};

  const TARGET_LABELS = {
    ac: 'AC',
    missile_thac0: 'Missile THAC0',
    melee_thac0: 'Melee THAC0',
  };

  function getModifierBadge(name) {
    const meta = abilityMeta[name];
    if (!meta || meta.type !== 'modifier') return null;
    const values = meta.values || [];
    const idx = Math.min(levelIndex, values.length - 1);
    const val = values[idx];
    if (!val) return null;
    const target = TARGET_LABELS[meta.target] || meta.target;
    const sign = val > 0 ? '+' : '';
    return `${target} ${sign}${val}`;
  }

  // --- Domain ---
  $: hasDomain = typeof classData.domain === 'string' && classData.domain.length > 0;

  // --- Item Abilities ---
  $: itemMods = character.combat_stats?.item_ability_modifiers ?? {};
  $: itemAuras = character.combat_stats?.item_auras ?? [];
  $: hasItemAbilities = Object.keys(itemMods).length > 0 || itemAuras.length > 0;

  const ITEM_TARGET_LABELS = {
    ac: 'AC', strength: 'STR', dexterity: 'DEX', wisdom: 'WIS',
    intelligence: 'INT', constitution: 'CON', charisma: 'CHA',
    missile_thac0: 'Missile THAC0', melee_thac0: 'Melee THAC0', movement_rate: 'Movement',
  };
</script>

<div class="space-y-6">
  {#if !hasAbilities && !hasDomain}
    <div class="panel">
      <p class="text-sm text-ink-faint">No class ability data available.</p>
    </div>
  {/if}

  <!-- Class Abilities -->
  {#if hasAbilities}
    <div class="panel">
      <h2 class="section-title">Class Abilities</h2>
      <ul class="space-y-3">
        {#each abilitiesEntries as [name, description]}
          {@const badge = getModifierBadge(name)}
          {@const meta = abilityMeta[name]}
          <li class="text-sm text-ink">
            <div class="flex items-center gap-2">
              <strong class="font-medium">{name}:</strong>
              {#if badge}
                <span class="inline-block text-xs font-bold px-1.5 py-0.5 rounded bg-parchment-200 border border-ink-faint text-ink">{badge}</span>
              {:else if meta?.type === 'special_attack'}
                <span class="inline-block text-xs font-bold px-1.5 py-0.5 rounded bg-parchment-200 border border-ink-faint text-ink">Weapon Attack</span>
              {/if}
            </div>
            <Markdown text={description} />
          </li>
        {/each}
      </ul>
    </div>
  {/if}

  <!-- Domain -->
  {#if hasDomain}
    <div class="panel">
      <h2 class="section-title">Domain (9th Level)</h2>
      <p class="text-sm text-ink whitespace-pre-line">{classData.domain}</p>
    </div>
  {/if}

  <!-- Item Abilities -->
  {#if hasItemAbilities}
    <div class="panel">
      <h2 class="section-title">Item Abilities</h2>

      {#if Object.keys(itemMods).length > 0}
        <div class="flex flex-wrap gap-2 mb-3">
          {#each Object.entries(itemMods) as [target, value]}
            {@const label = ITEM_TARGET_LABELS[target] || target}
            {@const sign = value > 0 ? '+' : ''}
            <span class="inline-block text-xs font-bold px-1.5 py-0.5 rounded bg-parchment-200 border border-ink-faint text-ink">
              {label} {sign}{value}
            </span>
          {/each}
        </div>
      {/if}

      {#if itemAuras.length > 0}
        <ul class="space-y-2">
          {#each itemAuras as aura}
            <li class="text-sm text-ink">
              <strong class="font-medium">{aura.item_name}:</strong>
              <Markdown text={aura.description} />
            </li>
          {/each}
        </ul>
      {/if}
    </div>
  {/if}
</div>
