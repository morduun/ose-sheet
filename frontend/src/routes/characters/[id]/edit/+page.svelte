<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api.js';
  import { token } from '$lib/stores.js';
  import { get } from 'svelte/store';
  import PageWrapper from '$lib/components/PageWrapper.svelte';

  const characterId = $page.params.id;

  let character = null;
  let campaign = null;
  let classes = [];
  let loading = true;
  let submitting = false;
  let error = '';

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

  let form = {};

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
      [character, classes] = await Promise.all([
        api.get(`/characters/${characterId}`),
        api.get('/character-classes/'),
      ]);
      // Fetch campaign for player list
      if (character.campaign_id) {
        campaign = await api.get(`/campaigns/${character.campaign_id}`);
      }
      form = {
        name: character.name ?? '',
        character_class_id: character.character_class_id ?? '',
        player_id: character.player_id ?? '',
        level: character.level ?? 1,
        alignment: character.alignment ?? 'Neutral',
        strength: character.strength ?? 10,
        intelligence: character.intelligence ?? 10,
        wisdom: character.wisdom ?? 10,
        dexterity: character.dexterity ?? 10,
        constitution: character.constitution ?? 10,
        charisma: character.charisma ?? 10,
        hp_max: character.hp_max ?? 4,
        hp_current: character.hp_current ?? 4,
        xp: character.xp ?? 0,
      };
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  async function submit() {
    if (!form.name.trim()) { error = 'Name is required.'; return; }
    submitting = true;
    error = '';
    try {
      const payload = {
        ...form,
        name: form.name.trim(),
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
      await api.patch(`/characters/${characterId}`, payload);
      goto(`/characters/${characterId}`);
    } catch (e) {
      error = e.message;
      submitting = false;
    }
  }
</script>

<svelte:head>
  <title>Edit {character?.name ?? 'Character'} — OSE Sheet</title>
</svelte:head>

<PageWrapper title="Edit Character">
  {#if loading}
    <p class="text-ink-faint">Loading…</p>
  {:else if error && !character}
    <p class="text-red-700">{error}</p>
  {:else}
    <div class="panel max-w-2xl">
      <div class="grid gap-4 sm:grid-cols-2">
        <!-- Name -->
        <div class="sm:col-span-2">
          <label class="block text-sm text-ink mb-1" for="edit-name">Name</label>
          <input id="edit-name" class="input w-full" type="text" bind:value={form.name} />
        </div>

        <!-- Class -->
        <div>
          <label class="block text-sm text-ink mb-1" for="edit-class">Class</label>
          <select id="edit-class" class="input w-full" bind:value={form.character_class_id}>
            {#each classes as cls}
              <option value={cls.id}>{cls.name}</option>
            {/each}
          </select>
        </div>

        <!-- Level -->
        <div>
          <label class="block text-sm text-ink mb-1" for="edit-level">Level</label>
          <input id="edit-level" class="input w-full" type="number" min="1" max="14" bind:value={form.level} />
        </div>

        <!-- Owner (GM only) -->
        {#if isGM && campaignMembers.length > 0}
          <div>
            <label class="block text-sm text-ink mb-1" for="edit-owner">Owner</label>
            <select id="edit-owner" class="input w-full" bind:value={form.player_id}>
              {#each campaignMembers as member}
                <option value={member.id}>{member.name}</option>
              {/each}
            </select>
          </div>
        {/if}

        <!-- Alignment -->
        <div>
          <label class="block text-sm text-ink mb-1" for="edit-align">Alignment</label>
          <select id="edit-align" class="input w-full" bind:value={form.alignment}>
            {#each alignments as a}
              <option value={a}>{a}</option>
            {/each}
          </select>
        </div>

        <!-- XP -->
        <div>
          <label class="block text-sm text-ink mb-1" for="edit-xp">XP</label>
          <input id="edit-xp" class="input w-full" type="number" min="0" bind:value={form.xp} />
        </div>

        <!-- Ability Scores -->
        <div class="sm:col-span-2">
          <p class="section-title">Ability Scores</p>
          <div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {#each abilityScores as { key, label }}
              <div>
                <label class="block text-xs text-ink-faint mb-1" for="edit-{key}">{label}</label>
                <input
                  id="edit-{key}"
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
          <label class="block text-sm text-ink mb-1" for="edit-maxhp">Max HP</label>
          <input id="edit-maxhp" class="input w-full" type="number" min="1" bind:value={form.hp_max} />
        </div>
        <div>
          <label class="block text-sm text-ink mb-1" for="edit-curhp">Current HP</label>
          <input id="edit-curhp" class="input w-full" type="number" bind:value={form.hp_current} />
        </div>
      </div>

      {#if error}
        <p class="text-red-700 text-sm mt-4">{error}</p>
      {/if}

      <div class="flex gap-3 mt-6">
        <button class="btn" on:click={submit} disabled={submitting}>
          {submitting ? 'Saving…' : 'Save Changes'}
        </button>
        <a href="/characters/{characterId}" class="btn-ghost">Cancel</a>
      </div>
    </div>
  {/if}
</PageWrapper>
