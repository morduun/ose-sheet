<script>
  export let label = '';
  export let variant = 'default'; // 'default' | 'gm' | 'player'
</script>

<span
  class="inline-block text-xs px-2 py-0.5 rounded-full font-sans"
  class:bg-ink={variant === 'gm'}
  class:text-parchment-50={variant === 'gm'}
  class:bg-parchment-200={variant === 'default' || variant === 'player'}
  class:text-ink-light={variant === 'default' || variant === 'player'}
>
  {label}
</span>
