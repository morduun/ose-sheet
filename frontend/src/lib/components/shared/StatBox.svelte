<script>
  export let label = '';
  export let score = 0;
  export let modifiers = {};
  export let clickable = false;
</script>

<div class="flex flex-col items-center border border-ink-faint rounded-sm bg-parchment-50 p-3 h-full transition-colors"
  class:hover-highlight={clickable}
>
  <span class="text-sm text-ink-faint uppercase tracking-wide font-sans">{label}</span>
  <span class="font-serif text-3xl text-ink leading-tight">{score}</span>
  {#if modifiers && Object.keys(modifiers).length}
    <div class="mt-1.5 grid grid-cols-[auto_auto] gap-x-2 gap-y-0.5 text-sm text-ink-light">
      {#each Object.entries(modifiers) as [key, val]}
        <span class="text-right truncate">{key}</span>
        <span class="text-left font-medium">{typeof val === 'boolean' ? (val ? 'Yes' : 'No') : typeof val === 'number' && val >= 0 ? `+${val}` : val}</span>
      {/each}
    </div>
  {/if}
</div>

<style>
  .hover-highlight:hover {
    background-color: #f9efd6;
  }
</style>
