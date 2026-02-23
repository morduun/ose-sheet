<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { browser } from '$app/environment';
  import { api } from '$lib/api.js';
  import { isAdmin } from '$lib/stores.js';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import ClassDetail from '$lib/components/classes/ClassDetail.svelte';

  // Admin guard
  $: if (browser && $isAdmin === false) goto('/campaigns');

  const classId = $page.params.id;

  let cls = null;
  let loading = true;
  let error = '';
  let deleteError = '';
  let confirmDelete = false;

  onMount(async () => {
    try {
      cls = await api.get(`/character-classes/${classId}`);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  async function handleDelete() {
    try {
      await api.delete(`/character-classes/${classId}`);
      goto('/classes');
    } catch (e) {
      deleteError = e.message;
      confirmDelete = false;
    }
  }
</script>

<svelte:head>
  <title>{cls?.name || 'Class'} — OSE Sheet</title>
</svelte:head>

<PageWrapper maxWidth="max-w-6xl">
  {#if loading}
    <p class="text-ink-faint">Loading...</p>
  {:else if error}
    <p class="text-red-700">{error}</p>
  {:else if cls}
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="font-serif text-3xl text-ink">{cls.name}</h1>
      </div>
      <div class="flex gap-2">
        <a href="/classes/{classId}/edit" class="btn">Edit</a>
        {#if confirmDelete}
          <button class="btn-danger" on:click={handleDelete}>Confirm Delete</button>
          <button class="btn-ghost" on:click={() => confirmDelete = false}>Cancel</button>
        {:else}
          <button class="btn-danger" on:click={() => confirmDelete = true}>Delete</button>
        {/if}
      </div>
    </div>

    {#if deleteError}
      <p class="text-red-700 text-sm mb-4">{deleteError}</p>
    {/if}

    <ClassDetail {cls} />
  {/if}
</PageWrapper>
