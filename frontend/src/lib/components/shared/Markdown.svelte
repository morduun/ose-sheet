<script>
  import { marked } from 'marked';

  export let text = '';

  marked.setOptions({ breaks: true, gfm: true });

  $: html = marked.parse(text || '');
</script>

<div class="md-content">{@html html}</div>

<style>
  .md-content :global(p) { margin: 0.25em 0; }
  .md-content :global(ul), .md-content :global(ol) { margin: 0.25em 0; padding-left: 1.5em; }
  .md-content :global(ul) { list-style: disc; }
  .md-content :global(ol) { list-style: decimal; }
  .md-content :global(li) { margin: 0.1em 0; }
  .md-content :global(strong) { font-weight: 600; }
  .md-content :global(em) { font-style: italic; }
  .md-content :global(h1), .md-content :global(h2), .md-content :global(h3) { font-weight: 600; margin: 0.5em 0 0.25em; }
  .md-content :global(blockquote) { border-left: 3px solid currentColor; padding-left: 0.75em; opacity: 0.8; margin: 0.5em 0; }
  .md-content :global(code) { background: rgba(0,0,0,0.06); padding: 0.1em 0.3em; border-radius: 2px; font-size: 0.9em; }
  .md-content :global(table) { border-collapse: collapse; margin: 0.5em 0; }
  .md-content :global(th), .md-content :global(td) { border: 1px solid rgba(0,0,0,0.15); padding: 0.25em 0.5em; text-align: left; }
</style>
