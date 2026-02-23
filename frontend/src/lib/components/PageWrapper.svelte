<script>
  export let title = '';
  export let maxWidth = 'max-w-4xl';
</script>

<div class="min-h-screen">
  <div class="{maxWidth} mx-auto px-4 py-6">
    {#if title}
      <h1 class="font-serif text-3xl text-ink mb-6">{title}</h1>
    {/if}
    <slot />
  </div>
</div>
