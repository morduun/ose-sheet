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
    <div class="panel {maxWidth} w-full mx-4 max-h-[80vh] flex flex-col modal-panel">
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

<style>
  .modal-panel {
    background: rgb(var(--color-parchment-50, 250 245 235)) !important;
    border: 1px solid rgba(107, 92, 74, 0.2) !important;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25) !important;
  }
</style>
