<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api.js';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import Modal from '$lib/components/shared/Modal.svelte';
  import ClassDetail from '$lib/components/classes/ClassDetail.svelte';

  import { token } from '$lib/stores.js';
  import { get } from 'svelte/store';

  const campaignId = parseInt($page.params.id);

  let classes = [];
  let campaign = null;
  let loading = true;
  let submitting = false;
  let error = '';

  // Class preview modal state
  let showClassPreview = false;
  let previewIndex = 0;

  // Attribute key mapping for requirement checks
  const ATTR_KEY = {
    STR: 'strength',
    INT: 'intelligence',
    WIS: 'wisdom',
    DEX: 'dexterity',
    CON: 'constitution',
    CHA: 'charisma',
  };

  function getUserId() {
    const t = get(token);
    if (!t) return null;
    try {
      const payload = JSON.parse(atob(t.split('.')[1]));
      return payload.sub ? parseInt(payload.sub) : null;
    } catch {
      return null;
    }
  }

  const userId = getUserId();
  $: isGM = campaign && userId && campaign.gm_id === userId;
  $: campaignMembers = campaign
    ? [
        ...(campaign.gm ? [campaign.gm] : []),
        ...(campaign.players || []),
      ]
    : [];

  let form = {
    name: '',
    character_class_id: '',
    player_id: '',
    level: 1,
    alignment: 'Neutral',
    strength: 10,
    intelligence: 10,
    wisdom: 10,
    dexterity: 10,
    constitution: 10,
    charisma: 10,
    hp_max: 4,
    hp_current: 4,
    xp: 0,
  };

  const alignments = ['Lawful', 'Neutral', 'Chaotic'];

  const abilityScores = [
    { key: 'strength', label: 'Strength' },
    { key: 'intelligence', label: 'Intelligence' },
    { key: 'wisdom', label: 'Wisdom' },
    { key: 'dexterity', label: 'Dexterity' },
    { key: 'constitution', label: 'Constitution' },
    { key: 'charisma', label: 'Charisma' },
  ];

  onMount(async () => {
    try {
      [classes, campaign] = await Promise.all([
        api.get('/character-classes/'),
        api.get(`/campaigns/${campaignId}`),
      ]);
      if (classes.length > 0) form.character_class_id = classes[0].id;
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  // Derived: currently selected class object
  $: selectedClass = classes.find(c => c.id == form.character_class_id) || null;

  // Derived: previewed class from index
  $: previewedClass = classes[previewIndex] || null;

  /** Check if player's scores meet a class's attribute requirements */
  function meetsRequirements(cls) {
    const reqs = cls?.class_data?.Requirements;
    if (!reqs || Object.keys(reqs).length === 0) return true;
    return Object.entries(reqs).every(([attr, min]) => {
      const formKey = ATTR_KEY[attr];
      return formKey && parseInt(form[formKey]) >= min;
    });
  }

  /** Return array of unmet requirement strings like ["CHA 17"] */
  function getUnmetReqs(cls) {
    const reqs = cls?.class_data?.Requirements;
    if (!reqs) return [];
    return Object.entries(reqs)
      .filter(([attr, min]) => {
        const formKey = ATTR_KEY[attr];
        return formKey && parseInt(form[formKey]) < min;
      })
      .map(([attr, min]) => `${attr} ${min}`);
  }

  /** Build the label shown for each option in the dropdown */
  function classOptionLabel(cls) {
    const unmet = getUnmetReqs(cls);
    if (unmet.length === 0) return cls.name;
    return `${cls.name} (requires ${unmet.join(', ')})`;
  }

  function openPreview(cls) {
    if (!cls) return;
    previewIndex = classes.indexOf(cls);
    if (previewIndex === -1) previewIndex = 0;
    showClassPreview = true;
  }

  function prevClass() {
    previewIndex = (previewIndex - 1 + classes.length) % classes.length;
  }

  function nextClass() {
    previewIndex = (previewIndex + 1) % classes.length;
  }

  async function submit() {
    if (!form.name.trim()) { error = 'Name is required.'; return; }
    if (!form.character_class_id) { error = 'Class is required.'; return; }
    submitting = true;
    error = '';
    try {
      const payload = {
        ...form,
        name: form.name.trim(),
        campaign_id: campaignId,
        character_class_id: parseInt(form.character_class_id),
        level: parseInt(form.level),
        strength: parseInt(form.strength),
        intelligence: parseInt(form.intelligence),
        wisdom: parseInt(form.wisdom),
        dexterity: parseInt(form.dexterity),
        constitution: parseInt(form.constitution),
        charisma: parseInt(form.charisma),
        hp_max: parseInt(form.hp_max),
        hp_current: parseInt(form.hp_current),
        xp: parseInt(form.xp),
      };
      if (form.player_id) payload.player_id = parseInt(form.player_id);
      else delete payload.player_id;
      const char = await api.post('/characters/', payload);
      goto(`/characters/${char.id}`);
    } catch (e) {
      error = e.message;
      submitting = false;
    }
  }
</script>

<svelte:head>
  <title>New Character — OSE Sheet</title>
</svelte:head>

<PageWrapper title="New Character">
  {#if loading}
    <p class="text-ink-faint">Loading…</p>
  {:else}
    <div class="panel max-w-2xl">
      <div class="grid gap-4 sm:grid-cols-2">
        <!-- Name -->
        <div class="sm:col-span-2">
          <label class="block text-sm text-ink mb-1" for="char-name">Name</label>
          <input id="char-name" class="input w-full" type="text" placeholder="Tordek Ironforge" bind:value={form.name} />
        </div>

        <!-- Class -->
        <div>
          <label class="block text-sm text-ink mb-1" for="char-class">Class</label>
          <div class="flex gap-2">
            <select id="char-class" class="input flex-1" bind:value={form.character_class_id}>
              {#each classes as cls}
                <option value={cls.id} disabled={!meetsRequirements(cls)}>
                  {classOptionLabel(cls)}
                </option>
              {/each}
            </select>
            <button
              type="button"
              class="btn-ghost text-xs px-2"
              on:click={() => openPreview(selectedClass)}
              title="Preview class details"
            >Preview</button>
          </div>
        </div>

        <!-- Level -->
        <div>
          <label class="block text-sm text-ink mb-1" for="char-level">Level</label>
          <input id="char-level" class="input w-full" type="number" min="1" max="14" bind:value={form.level} />
        </div>

        <!-- Owner (GM only) -->
        {#if isGM && campaignMembers.length > 0}
          <div>
            <label class="block text-sm text-ink mb-1" for="char-owner">Owner</label>
            <select id="char-owner" class="input w-full" bind:value={form.player_id}>
              <option value="">Myself</option>
              {#each campaignMembers as member}
                {#if member.id !== userId}
                  <option value={member.id}>{member.name}</option>
                {/if}
              {/each}
            </select>
          </div>
        {/if}

        <!-- Alignment -->
        <div>
          <label class="block text-sm text-ink mb-1" for="char-align">Alignment</label>
          <select id="char-align" class="input w-full" bind:value={form.alignment}>
            {#each alignments as a}
              <option value={a}>{a}</option>
            {/each}
          </select>
        </div>

        <!-- XP -->
        <div>
          <label class="block text-sm text-ink mb-1" for="char-xp">Starting XP</label>
          <input id="char-xp" class="input w-full" type="number" min="0" bind:value={form.xp} />
        </div>

        <!-- Ability Scores -->
        <div class="sm:col-span-2">
          <p class="section-title">Ability Scores</p>
          <div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {#each abilityScores as { key, label }}
              <div>
                <label class="block text-xs text-ink-faint mb-1" for="score-{key}">{label}</label>
                <input
                  id="score-{key}"
                  class="input w-full"
                  type="number"
                  min="3"
                  max="18"
                  bind:value={form[key]}
                />
              </div>
            {/each}
          </div>
        </div>

        <!-- HP -->
        <div>
          <label class="block text-sm text-ink mb-1" for="char-maxhp">Max HP</label>
          <input id="char-maxhp" class="input w-full" type="number" min="1" bind:value={form.hp_max} />
        </div>
        <div>
          <label class="block text-sm text-ink mb-1" for="char-curhp">Current HP</label>
          <input id="char-curhp" class="input w-full" type="number" bind:value={form.hp_current} />
        </div>
      </div>

      {#if error}
        <p class="text-red-700 text-sm mt-4">{error}</p>
      {/if}

      <div class="flex gap-3 mt-6">
        <button class="btn" on:click={submit} disabled={submitting}>
          {submitting ? 'Creating…' : 'Create Character'}
        </button>
        <a href="/campaigns/{campaignId}" class="btn-ghost">Cancel</a>
      </div>
    </div>
  {/if}
</PageWrapper>

<!-- Class Preview Modal -->
<Modal bind:open={showClassPreview} title={previewedClass?.name ?? 'Class'} maxWidth="max-w-6xl">
  {#if previewedClass && !meetsRequirements(previewedClass)}
    <div class="mb-4 p-3 rounded border border-amber-400 bg-amber-50 text-amber-900 text-sm">
      Does not meet requirements: {getUnmetReqs(previewedClass).join(', ')}
    </div>
  {/if}

  <div class="flex items-center justify-between mb-4">
    <button type="button" class="btn-ghost text-sm" on:click={prevClass}>&#8592; Previous</button>
    <span class="text-sm text-ink-faint">{previewIndex + 1} / {classes.length}</span>
    <button type="button" class="btn-ghost text-sm" on:click={nextClass}>Next &#8594;</button>
  </div>

  {#if previewedClass}
    <ClassDetail cls={previewedClass} />
  {/if}
</Modal>
