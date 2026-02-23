<script>
  export let open = false;
  export let title = '';
  export let maxWidth = 'max-w-lg';

  function close() {
    open = false;
  }

  function onKeydown(e) {
    if (e.key === 'Escape') close();
  }
</script>

{#if open}
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-ink/50"
    on:click|self={close}
    on:keydown={onKeydown}
  >
    <div class="panel {maxWidth} w-full mx-4 max-h-[80vh] flex flex-col">
      <div class="flex items-center justify-between mb-4">
        <h2 class="section-title mb-0 border-none pb-0">{title}</h2>
        <button class="btn-ghost text-xs px-2 py-0.5" on:click={close}>✕</button>
      </div>
      <div class="overflow-y-auto flex-1">
        <slot />
      </div>
    </div>
  </div>
{/if}
