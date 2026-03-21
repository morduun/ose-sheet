<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { token, fetchUserInfo } from '$lib/stores.js';

  let error = '';

  onMount(async () => {
    const err = $page.url.searchParams.get('error');
    if (err === 'not_allowed') {
      error = 'This email is not authorized to access this server. Contact the GM for an invite.';
      return;
    }

    const t = $page.url.searchParams.get('token');
    if (!t) {
      error = 'No token received from Google. Please try again.';
      return;
    }

    token.set(t);
    await fetchUserInfo();
    goto('/campaigns');
  });
</script>

<svelte:head>
  <title>Signing in… — OSE Sheet</title>
</svelte:head>

<div class="min-h-screen flex flex-col items-center justify-center px-4">
  {#if error}
    <div class="panel max-w-sm text-center">
      <p class="text-red-700 mb-4">{error}</p>
      <a href="/" class="btn">Back to login</a>
    </div>
  {:else}
    <p class="text-ink-faint">Signing in…</p>
  {/if}
</div>
