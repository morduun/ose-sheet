<script>
  import { goto } from '$app/navigation';
  import { browser } from '$app/environment';
  import { api } from '$lib/api.js';
  import { isAdmin } from '$lib/stores.js';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import MonsterForm from '$lib/components/monsters/MonsterForm.svelte';

  // Admin guard
  $: if (browser && $isAdmin === false) goto('/campaigns');

  async function handleSubmit(payload) {
    const created = await api.post('/monsters/', { ...payload, is_default: true });
    goto(`/monsters/${created.id}`);
  }
</script>

<svelte:head>
  <title>New Monster — OSE Sheet</title>
</svelte:head>

<PageWrapper title="New Monster">
  <MonsterForm onSubmit={handleSubmit} />
</PageWrapper>
