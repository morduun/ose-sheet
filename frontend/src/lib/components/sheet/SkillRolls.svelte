<script>
  export let character;
  export let rollDice = null;

  $: classData = character.character_class?.class_data ?? {};
  $: levelIndex = Math.max(0, (character.level ?? 1) - 1);

  // --- Thief / Class Skills ---
  const skillLabels = {
    climb_surface: 'Climb Surfaces',
    find_traps: 'Find/Remove Traps',
    hear_noise: 'Hear Noise',
    hide_shadows: 'Hide in Shadows',
    move_silent: 'Move Silently',
    open_locks: 'Open Locks',
    pick_pockets: 'Pick Pockets',
    falling: 'Falling',
    tightrope_walking: 'Tightrope Walking',
    assassination: 'Assassination',
    agile_fighting: 'Agile Fighting',
    hide_undergrowth: 'Hide in Undergrowth',
    lay_on_hands: 'Lay on Hands',
    tracking: 'Tracking',
  };

  function getSkillValue(skillKey) {
    const arr = classData.thief_skills?.[skillKey];
    if (!arr || !Array.isArray(arr)) return 0;
    const idx = Math.min(levelIndex, arr.length - 1);
    return arr[idx] ?? 0;
  }

  function formatSkill(skillKey, value) {
    if (skillKey === 'hear_noise') return `${value}-in-6`;
    return `${value}%`;
  }

  $: visibleSkills = Object.entries(skillLabels).filter(
    ([key]) => getSkillValue(key) > 0
  );

  $: hasThiefSkills = classData.thief_skills
    ? Object.entries(classData.thief_skills).some(
        ([key, arr]) => key !== 'hear_noise' && Array.isArray(arr) && arr[Math.min(levelIndex, arr.length - 1)] > 0
      )
    : false;

  // --- Ability Metadata Skill Rolls ---
  $: abilityMeta = classData.ability_metadata ?? {};

  function getAllAbilitySkillRolls() {
    const results = [];
    for (const [name, meta] of Object.entries(abilityMeta)) {
      if (!meta || meta.type !== 'skill') continue;
      for (const [rName, r] of Object.entries(meta.rolls || {})) {
        results.push({
          abilityName: name,
          name: rName,
          chance: r.chance,
          die: r.die || 6,
        });
      }
    }
    return results;
  }

  $: abilitySkillRolls = getAllAbilitySkillRolls();
  $: hasAbilitySkills = abilitySkillRolls.length > 0;

  // --- Turn Undead ---
  const hdLabels = {
    '1hd': '1 HD',
    '2hd': '2 HD',
    '2+hd': '2+ HD',
    '3hd': '3 HD',
    '4hd': '4 HD',
    '5hd': '5 HD',
    '6hd': '6 HD',
    '7hd': '7 HD',
    '8hd': '8 HD',
    '9hd': '9 HD',
    '10hd': '10 HD',
    '11hd': '11 HD',
    '12+hd': '12+ HD',
  };

  function getTurningValue(hdKey) {
    const arr = classData.turning?.[hdKey];
    if (!arr || !Array.isArray(arr)) return '-';
    const idx = Math.min(levelIndex, arr.length - 1);
    return arr[idx] ?? '-';
  }

  // Filter to only HD categories the character can affect at current level
  $: turningEntries = Object.entries(hdLabels)
    .map(([key, label]) => ({ key, label, value: getTurningValue(key) }))
    .filter(e => e.value !== '-');

  $: hasTurning = turningEntries.length > 0;

  $: hasSkills = hasThiefSkills || hasAbilitySkills || hasTurning;
</script>

<div class="space-y-6">
  {#if !hasSkills}
    <div class="panel">
      <p class="text-sm text-ink-faint">No skill rolls available.</p>
    </div>
  {/if}

  <!-- Class Skills (thief skills) -->
  {#if hasThiefSkills}
    <div class="panel">
      <h2 class="section-title">Class Skills</h2>
      <div class="flex flex-wrap justify-center gap-3">
        {#each visibleSkills as [key, label]}
          <button
            class="flex flex-col items-center border border-ink-faint rounded-sm bg-parchment-50 p-3 min-w-[120px]
                   cursor-pointer hover:bg-parchment-100 transition-colors"
            disabled={!rollDice}
            on:click={() => {
              if (!rollDice) return;
              const target = getSkillValue(key);
              if (key === 'hear_noise') {
                rollDice('1d6', (roll) =>
                  roll <= target
                    ? `Success! (${roll} \u2264 ${target})`
                    : `Failure! (${roll} > ${target})`
                );
              } else {
                rollDice('1d100', (roll) =>
                  roll <= target
                    ? `Success! (${roll}% \u2264 ${target}%)`
                    : `Failure! (${roll}% > ${target}%)`
                );
              }
            }}
          >
            <span class="text-sm text-ink-faint uppercase tracking-wide font-sans">{label}</span>
            <span class="font-serif text-3xl text-ink leading-tight">{formatSkill(key, getSkillValue(key))}</span>
          </button>
        {/each}
      </div>
    </div>
  {/if}

  <!-- Ability Skill Rolls -->
  {#if hasAbilitySkills}
    <div class="panel">
      <h2 class="section-title">Special Skills</h2>
      <div class="flex flex-wrap justify-center gap-3">
        {#each abilitySkillRolls as roll}
          <button
            class="flex flex-col items-center border border-ink-faint rounded-sm bg-parchment-50 p-3 min-w-[120px]
                   cursor-pointer hover:bg-parchment-100 transition-colors"
            disabled={!rollDice}
            on:click={() => {
              if (!rollDice) return;
              const target = roll.chance;
              const dieStr = roll.die === 100 ? '1d100' : `1d${roll.die}`;
              rollDice(dieStr, (result) =>
                result <= target
                  ? `Success! (${result} \u2264 ${target})`
                  : `Failure! (${result} > ${target})`
              );
            }}
          >
            <span class="text-sm text-ink-faint uppercase tracking-wide font-sans">{roll.name}</span>
            <span class="font-serif text-xl text-ink leading-tight">
              {roll.die === 100 ? `${roll.chance}%` : `${roll.chance}-in-${roll.die}`}
            </span>
          </button>
        {/each}
      </div>
    </div>
  {/if}

  <!-- Turn Undead -->
  {#if hasTurning}
    <div class="panel">
      <h2 class="section-title">Turn Undead</h2>
      <div class="flex flex-wrap justify-center gap-3">
        {#each turningEntries as entry}
          {@const isAuto = entry.value === 'T' || entry.value === 'D'}
          <button
            class="flex flex-col items-center border border-ink-faint rounded-sm bg-parchment-50 p-3 min-w-[80px]
                   transition-colors"
            class:cursor-pointer={!isAuto && rollDice}
            class:hover:bg-parchment-100={!isAuto}
            disabled={isAuto || !rollDice}
            on:click={() => {
              if (isAuto || !rollDice) return;
              const target = parseInt(entry.value);
              rollDice('2d6', (roll) =>
                roll >= target
                  ? `Turned! (${roll} \u2265 ${target})`
                  : `Failed (${roll} < ${target})`
              );
            }}
          >
            <span class="text-sm text-ink-faint uppercase tracking-wide font-sans">{entry.label}</span>
            <span class="font-serif text-2xl leading-tight"
              class:text-green-800={entry.value === 'D'}
              class:text-ink={entry.value !== 'D'}
            >
              {#if entry.value === 'T'}
                Turned
              {:else if entry.value === 'D'}
                Destroy
              {:else}
                {entry.value}+
              {/if}
            </span>
            {#if !isAuto}
              <span class="text-xs text-ink-faint">2d6</span>
            {/if}
          </button>
        {/each}
      </div>
      <p class="text-xs text-ink-faint mt-3 text-center">
        Click a number to roll 2d6. Turned/Destroy are automatic.
      </p>
    </div>
  {/if}
</div>
