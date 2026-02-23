<script>
  import { token, isLoggedIn, fetchUserInfo } from '$lib/stores.js';
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';

  let email = '';
  let name = '';
  let error = '';
  let loggingIn = false;

  onMount(() => {
    if ($isLoggedIn) goto('/campaigns');
  });

  async function login() {
    error = '';
    const e = email.trim();
    if (!e) {
      error = 'Please enter your email.';
      return;
    }
    loggingIn = true;
    try {
      const res = await api.post('/auth/token', {
        email: e,
        name: name.trim() || null,
      });
      token.set(res.access_token);
      await fetchUserInfo();
      goto('/campaigns');
    } catch (err) {
      error = err.message;
    } finally {
      loggingIn = false;
    }
  }

  function onKeydown(e) {
    if (e.key === 'Enter') login();
  }
</script>

<svelte:head>
  <title>OSE Sheet</title>
</svelte:head>

<div class="min-h-screen flex flex-col items-center justify-center px-4">
  <div class="text-center mb-8">
    <h1 class="font-serif text-5xl text-ink mb-3">OSE Character Sheet</h1>
    <p class="text-ink-faint max-w-md">
      Old-School Essentials character management for players and game masters.
    </p>
  </div>

  <div class="panel w-full max-w-sm">
    <h2 class="section-title">Sign In</h2>
    <div class="flex flex-col gap-3">
      <div>
        <label for="email" class="text-xs text-ink-faint uppercase tracking-wide">Email</label>
        <input
          id="email"
          class="input w-full mt-1"
          type="email"
          placeholder="you@example.com"
          bind:value={email}
          on:keydown={onKeydown}
        />
      </div>
      <div>
        <label for="name" class="text-xs text-ink-faint uppercase tracking-wide">Name</label>
        <input
          id="name"
          class="input w-full mt-1"
          type="text"
          placeholder="Your character name"
          bind:value={name}
          on:keydown={onKeydown}
        />
        <p class="text-xs text-ink-faint mt-1">Optional — used to identify you in campaigns.</p>
      </div>
      {#if error}
        <p class="text-red-700 text-xs">{error}</p>
      {/if}
      <button class="btn" on:click={login} disabled={loggingIn}>
        {loggingIn ? 'Signing in…' : 'Sign In'}
      </button>
    </div>
  </div>
</div>
