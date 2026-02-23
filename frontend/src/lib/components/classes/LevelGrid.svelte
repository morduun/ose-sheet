<script>
  /**
   * Reusable spreadsheet grid for level-indexed data.
   * @prop rows - [{key, label}] defining row labels
   * @prop columns - number of level columns (from max_level)
   * @prop data - object of arrays {rowKey: [val, val, ...]}
   * @prop inputType - 'number' (default) or 'text'
   * @prop readonly - renders plain text instead of inputs
   */
  export let rows = [];
  export let columns = 14;
  export let data = {};
  export let inputType = 'number';
  export let readonly = false;
</script>

<div class="overflow-x-auto border border-ink-faint rounded-sm">
  <table class="text-xs border-collapse w-full">
    <thead>
      <tr class="bg-parchment-200">
        <th class="sticky left-0 z-10 bg-parchment-200 px-2 py-1 text-left text-ink-faint font-medium border-r border-ink-faint min-w-[120px]">
          Level
        </th>
        {#each Array(columns) as _, i}
          <th class="px-1 py-1 text-center text-ink-faint font-medium min-w-[3.5rem]">
            {i + 1}
          </th>
        {/each}
      </tr>
    </thead>
    <tbody>
      {#each rows as row, ri}
        <tr class:bg-parchment-100={ri % 2 === 0} class:bg-parchment-50={ri % 2 !== 0}>
          <td class="sticky left-0 z-10 px-2 py-1 text-ink font-medium border-r border-ink-faint whitespace-nowrap"
              class:bg-parchment-100={ri % 2 === 0}
              class:bg-parchment-50={ri % 2 !== 0}>
            {row.label}
          </td>
          {#each Array(columns) as _, ci}
            <td class="px-0.5 py-0.5 text-center">
              {#if readonly}
                <span class="inline-block w-14 text-center text-ink">
                  {data[row.key]?.[ci] ?? ''}
                </span>
              {:else if inputType === 'number'}
                <input
                  type="number"
                  class="input w-14 text-center text-xs px-1 py-0.5"
                  bind:value={data[row.key][ci]}
                />
              {:else}
                <input
                  type="text"
                  class="input w-14 text-center text-xs px-1 py-0.5"
                  bind:value={data[row.key][ci]}
                />
              {/if}
            </td>
          {/each}
        </tr>
      {/each}
    </tbody>
  </table>
</div>
