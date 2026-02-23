<script>
  import { goto } from '$app/navigation';
  import { browser } from '$app/environment';
  import { api } from '$lib/api.js';
  import { isAdmin } from '$lib/stores.js';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import ClassForm from '$lib/components/classes/ClassForm.svelte';

  // Admin guard
  $: if (browser && $isAdmin === false) goto('/campaigns');

  async function handleSubmit(payload) {
    const created = await api.post('/character-classes/', payload);
    goto(`/classes/${created.id}`);
  }
</script>

<svelte:head>
  <title>New Class — OSE Sheet</title>
</svelte:head>

<PageWrapper title="New Character Class" maxWidth="max-w-6xl">
  <ClassForm onSubmit={handleSubmit} />
</PageWrapper>
