<script>
  import { isLoggedIn, isAdmin, token, theme } from '$lib/stores.js';
  import { goto } from '$app/navigation';

  function logout() {
    token.clear();
    goto('/');
  }
</script>

<nav class="print:hidden bg-ink text-parchment-50 px-4 py-2 flex items-center gap-6">
  <a href="/" class="font-serif text-xl text-parchment-100 hover:text-parchment-50">
    OSE Sheet
  </a>
  {#if $isLoggedIn}
    <a href="/campaigns" class="text-sm text-parchment-200 hover:text-parchment-50 transition-colors">
      Campaigns
    </a>
    {#if $isAdmin}
      <a href="/classes" class="text-sm text-parchment-200 hover:text-parchment-50 transition-colors">
        Classes
      </a>
      <a href="/spells" class="text-sm text-parchment-200 hover:text-parchment-50 transition-colors">
        Spells
      </a>
      <a href="/items" class="text-sm text-parchment-200 hover:text-parchment-50 transition-colors">
        Items
      </a>
      <a href="/monsters" class="text-sm text-parchment-200 hover:text-parchment-50 transition-colors">
        Monsters
      </a>
      <a href="/admin" class="text-sm text-parchment-200 hover:text-parchment-50 transition-colors">
        Admin
      </a>
    {/if}
    <div class="ml-auto flex items-center gap-4">
      <button
        class="text-sm text-parchment-200 hover:text-parchment-50 transition-colors"
        on:click={() => theme.toggle()}
        title="Switch theme"
      >
        {$theme === 'notebook' ? '\u{1F4DC}' : '\u{1F4D3}'}
      </button>
      <button
        class="text-sm text-parchment-200 hover:text-parchment-50 transition-colors"
        on:click={logout}
      >
        Log out
      </button>
    </div>
  {/if}
</nav>
