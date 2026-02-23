<script>
  import '../app.css';
  import Nav from '$lib/components/Nav.svelte';
  import { isLoggedIn, fetchUserInfo } from '$lib/stores.js';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { browser } from '$app/environment';
  import { onMount } from 'svelte';

  $: if (browser && !$isLoggedIn && $page.url.pathname !== '/' && !$page.url.pathname.startsWith('/auth/')) {
    goto('/');
  }

  onMount(() => {
    if ($isLoggedIn) fetchUserInfo();
  });
</script>

<Nav />
<slot />
