<script>
  import LevelGrid from '$lib/components/classes/LevelGrid.svelte';
  import Markdown from '$lib/components/shared/Markdown.svelte';

  export let cls;

  // Row definitions
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
  const allSkillRows = [
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

  const TARGET_LABELS = {
    ac: 'AC',
    missile_thac0: 'Missile THAC0',
    melee_thac0: 'Melee THAC0',
  };

  // Helpers
  function hasNonZero(obj, keys) {
    if (!obj) return false;
    return keys.some(k => obj[k]?.some(v => v !== 0));
  }
  function hasNonDash(obj, keys) {
    if (!obj) return false;
    return keys.some(k => obj[k]?.some(v => v !== '-'));
  }
  function rowHasData(obj, key) {
    if (!obj?.[key]) return false;
    if (key === 'hear_noise') return obj[key].some(v => v > 1);
    return obj[key].some(v => v !== 0);
  }

  // Reactive derivations
  $: cd = cls?.class_data || {};
  $: maxLevel = cd.max_level || 14;
  $: progressionData = { thac0: cd.thac0 || [], xp: cd.xp || [] };
  $: hasRequirements = cd.Requirements && Object.keys(cd.Requirements).length > 0;
  $: showSpells = hasNonZero(cd.spells, ['1st','2nd','3rd','4th','5th','6th']);
  $: showTurning = hasNonDash(cd.turning, ['1hd','2hd','2+hd','3hd','4hd','5hd','6hd','7hd','8hd','9hd','10hd','11hd','12+hd']);
  $: activeSkillRows = allSkillRows.filter(r => rowHasData(cd.thief_skills, r.key));
  $: showSkills = activeSkillRows.length > 0;
  $: hasAbilities = cd.abilities && Object.keys(cd.abilities).length > 0;
  $: abilityMeta = cd.ability_metadata || {};
  $: hasSpellLists = cd.spell_lists && cd.spell_lists.length > 0;
</script>

{#if cls.description}
  <p class="text-ink-light text-sm mb-4">{cls.description}</p>
{/if}

<!-- Basics -->
<div class="panel mb-4">
  <h2 class="section-title">Basics</h2>
  <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
    <div><span class="text-ink-faint">Hit Dice:</span> <strong>{cd.hit_dice}</strong></div>
    <div><span class="text-ink-faint">Max Level:</span> <strong>{maxLevel}</strong></div>
    <div><span class="text-ink-faint">Armor:</span> <strong>{cd.armor}</strong></div>
    <div><span class="text-ink-faint">Shields:</span> <strong>{cd.shields}</strong></div>
    <div><span class="text-ink-faint">Weapons:</span> <strong>{cd.weapons}</strong></div>
    <div><span class="text-ink-faint">HP Bonus (post-9th):</span> <strong>{cd.hp_bonus_post_9th ?? 0}</strong></div>
    {#if cd.prime_requisite?.length}
      <div><span class="text-ink-faint">Prime Req:</span> <strong>{cd.prime_requisite.join(', ')}</strong></div>
    {/if}
    {#if cd.languages?.length}
      <div><span class="text-ink-faint">Languages:</span> <strong>{cd.languages.join(', ')}</strong></div>
    {/if}
  </div>
  {#if hasRequirements}
    <div class="mt-3 pt-3 border-t border-ink-faint">
      <span class="text-sm text-ink-faint">Attribute Requirements:</span>
      <div class="flex gap-3 mt-1">
        {#each Object.entries(cd.Requirements) as [attr, min]}
          <span class="text-sm"><strong>{attr}</strong> {min}+</span>
        {/each}
      </div>
    </div>
  {/if}
</div>

<!-- Abilities -->
{#if hasAbilities}
  <div class="panel mb-4">
    <h2 class="section-title">Abilities</h2>
    <div class="flex flex-col gap-2">
      {#each Object.entries(cd.abilities) as [name, desc]}
        {@const meta = abilityMeta[name]}
        <div>
          <div class="flex items-center gap-2">
            <strong class="text-ink">{name}</strong>
            {#if meta?.type === 'modifier'}
              <span class="text-xs px-1.5 py-0.5 rounded bg-parchment-200 border border-ink-faint text-ink-faint">
                {TARGET_LABELS[meta.target] || meta.target} modifier: {Math.min(...meta.values)} to {Math.max(...meta.values)}
              </span>
            {:else if meta?.type === 'special_attack'}
              <span class="text-xs px-1.5 py-0.5 rounded bg-parchment-200 border border-ink-faint text-ink-faint">
                Weapon Attack
              </span>
            {/if}
          </div>
          <div class="text-sm text-ink-light"><Markdown text={desc} /></div>
          {#if meta?.type === 'skill' && meta.rolls}
            <div class="flex flex-wrap gap-2 mt-1">
              {#each Object.entries(meta.rolls) as [rName, r]}
                <span class="text-xs px-1.5 py-0.5 rounded bg-parchment-200 border border-ink-faint text-ink-faint">
                  {rName}: {r.chance}-in-{r.die || 6}
                </span>
              {/each}
            </div>
          {/if}
          {#if meta?.type === 'special_attack' && meta.attacks}
            <div class="flex flex-wrap gap-2 mt-1">
              {#each meta.attacks as atk}
                <span class="text-xs px-1.5 py-0.5 rounded bg-parchment-200 border border-ink-faint text-ink-faint">
                  {atk.name}{#if atk.hit_bonus} +{atk.hit_bonus} hit{/if}{#if atk.damage_multiplier} ×{atk.damage_multiplier} dmg{/if}{#if atk.effect} · {atk.effect}{/if}
                </span>
              {/each}
            </div>
          {/if}
        </div>
      {/each}
    </div>
  </div>
{/if}

<!-- Domain -->
{#if cd.domain}
  <div class="panel mb-4">
    <h2 class="section-title">Domain</h2>
    <p class="text-sm text-ink whitespace-pre-line">{cd.domain}</p>
  </div>
{/if}

<!-- Class Skills -->
{#if showSkills}
  <div class="panel mb-4">
    <h2 class="section-title">Class Skills</h2>
    <LevelGrid rows={activeSkillRows} columns={maxLevel} data={cd.thief_skills || {}} readonly />
  </div>
{/if}

<!-- Turn Undead -->
{#if showTurning}
  <div class="panel mb-4">
    <h2 class="section-title">Turn Undead</h2>
    <LevelGrid rows={turningRows} columns={maxLevel} data={cd.turning || {}} inputType="text" readonly />
  </div>
{/if}

<!-- Spell List Access -->
{#if hasSpellLists}
  <div class="panel mb-4">
    <h2 class="section-title">Spell List Access</h2>
    <div class="flex flex-wrap gap-3">
      {#each cd.spell_lists as sl}
        <span class="text-sm">
          <strong class="capitalize">{sl.list}</strong>
          {#if sl.from_level > 1}
            <span class="text-ink-faint">(from level {sl.from_level})</span>
          {/if}
        </span>
      {/each}
    </div>
  </div>
{/if}

<!-- Spell Slots -->
{#if showSpells}
  <div class="panel mb-4">
    <h2 class="section-title">Spell Slots</h2>
    <LevelGrid rows={spellRows} columns={maxLevel} data={cd.spells || {}} readonly />
  </div>
{/if}

<!-- Progression -->
<div class="panel mb-4">
  <h2 class="section-title">XP Requirements</h2>
  <LevelGrid rows={xpRows} columns={maxLevel} data={progressionData} readonly />
</div>
<div class="panel mb-4">
  <h2 class="section-title">THAC0</h2>
  <LevelGrid rows={thac0Rows} columns={maxLevel} data={progressionData} readonly />
</div>
<div class="panel mb-4">
  <h2 class="section-title">Saving Throws</h2>
  <LevelGrid rows={saveRows} columns={maxLevel} data={cd.saving_throws || {}} readonly />
</div>
