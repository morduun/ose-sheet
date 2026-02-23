<script>
  import { goto } from '$app/navigation';
  import { browser } from '$app/environment';
  import { api } from '$lib/api.js';
  import { isAdmin } from '$lib/stores.js';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import ItemForm from '$lib/components/items/ItemForm.svelte';

  // Admin guard
  $: if (browser && $isAdmin === false) goto('/campaigns');

  async function handleSubmit(payload) {
    const created = await api.post('/items/', { ...payload, is_default: true });
    goto(`/items/${created.id}`);
  }
</script>

<svelte:head>
  <title>New Item — OSE Sheet</title>
</svelte:head>

<PageWrapper title="New Item">
  <ItemForm onSubmit={handleSubmit} />
</PageWrapper>
