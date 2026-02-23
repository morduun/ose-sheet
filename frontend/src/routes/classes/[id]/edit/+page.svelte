<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { browser } from '$app/environment';
  import { api } from '$lib/api.js';
  import { isAdmin } from '$lib/stores.js';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import ClassForm from '$lib/components/classes/ClassForm.svelte';

  // Admin guard
  $: if (browser && $isAdmin === false) goto('/campaigns');

  const classId = $page.params.id;

  let cls = null;
  let loading = true;
  let error = '';

  onMount(async () => {
    try {
      cls = await api.get(`/character-classes/${classId}`);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  async function handleSubmit(payload) {
    await api.patch(`/character-classes/${classId}`, {
      name: payload.name,
      description: payload.description,
      class_data: payload.class_data,
    });
    goto(`/classes/${classId}`);
  }
</script>

<svelte:head>
  <title>Edit {cls?.name || 'Class'} — OSE Sheet</title>
</svelte:head>

<PageWrapper title="Edit {cls?.name || 'Class'}" maxWidth="max-w-6xl">
  {#if loading}
    <p class="text-ink-faint">Loading...</p>
  {:else if error}
    <p class="text-red-700">{error}</p>
  {:else if cls}
    <ClassForm
      initialName={cls.name}
      initialDescription={cls.description || ''}
      initialData={cls.class_data}
      onSubmit={handleSubmit}
    />
  {/if}
</PageWrapper>
