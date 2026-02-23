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
</div>
