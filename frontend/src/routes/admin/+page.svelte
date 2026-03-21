<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { browser } from '$app/environment';
  import { api } from '$lib/api.js';
  import { isAdmin } from '$lib/stores.js';
  import PageWrapper from '$lib/components/PageWrapper.svelte';

  let backups = [];
  let loading = true;
  let error = '';
  let message = '';
  let busy = false;
  let fileInput;

  // Allowlist state
  let allowedEmails = [];
  let newEmail = '';
  let addingEmail = false;

  $: if (browser && $isAdmin === false) goto('/campaigns');

  async function loadBackups() {
    try {
      backups = await api.get('/backups');
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    loadBackups();
    loadAllowedEmails();
  });

  async function loadAllowedEmails() {
    try {
      allowedEmails = await api.get('/allowed-emails');
    } catch {
      // silently fail — may not have permission
    }
  }

  async function addEmail() {
    const email = newEmail.trim().toLowerCase();
    if (!email) return;
    addingEmail = true;
    error = '';
    message = '';
    try {
      await api.post('/allowed-emails', { email });
      newEmail = '';
      message = `${email} added to allowlist`;
      await loadAllowedEmails();
    } catch (e) {
      error = e.message;
    } finally {
      addingEmail = false;
    }
  }

  async function removeEmail(entry) {
    if (!confirm(`Remove ${entry.email} from the allowlist? They will not be able to log in.`)) return;
    error = '';
    message = '';
    try {
      await api.delete(`/allowed-emails/${entry.id}`);
      message = `${entry.email} removed from allowlist`;
      await loadAllowedEmails();
    } catch (e) {
      error = e.message;
    }
  }

  async function createBackup() {
    busy = true;
    error = '';
    message = '';
    try {
      const result = await api.post('/backups');
      message = `Backup created: ${result.filename}`;
      await loadBackups();
    } catch (e) {
      error = e.message;
    } finally {
      busy = false;
    }
  }

  async function downloadBackup(filename) {
    try {
      const blob = await api.downloadBlob(`/backups/${filename}/download`);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      error = e.message;
    }
  }

  async function restoreBackup(filename) {
    if (!confirm(`Restore from ${filename}? This will replace the current database. A pre-restore backup will be created automatically.`)) return;
    busy = true;
    error = '';
    message = '';
    try {
      const result = await api.post(`/backups/restore/${filename}`);
      message = `${result.message} (pre-restore backup: ${result.pre_restore_backup})`;
      await loadBackups();
    } catch (e) {
      error = e.message;
    } finally {
      busy = false;
    }
  }

  async function uploadRestore() {
    const file = fileInput?.files?.[0];
    if (!file) return;
    if (!confirm(`Upload and restore from ${file.name}? This will replace the current database. A pre-restore backup will be created automatically.`)) return;
    busy = true;
    error = '';
    message = '';
    try {
      const result = await api.upload('/backups/upload-restore', file);
      message = `${result.message} (pre-restore backup: ${result.pre_restore_backup})`;
      fileInput.value = '';
      await loadBackups();
    } catch (e) {
      error = e.message;
    } finally {
      busy = false;
    }
  }

  async function deleteBackup(filename) {
    if (!confirm(`Delete backup ${filename}? This cannot be undone.`)) return;
    busy = true;
    error = '';
    message = '';
    try {
      await api.delete(`/backups/${filename}`);
      message = `Deleted ${filename}`;
      await loadBackups();
    } catch (e) {
      error = e.message;
    } finally {
      busy = false;
    }
  }

  function formatBytes(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function formatDate(iso) {
    return new Date(iso).toLocaleString();
  }
</script>

<svelte:head>
  <title>Admin — OSE Sheet</title>
</svelte:head>

<PageWrapper title="Admin">
  {#if error}
    <div class="panel border-red-800 bg-red-50 text-red-900 mb-4 p-3">{error}</div>
  {/if}

  {#if message}
    <div class="panel border-green-800 bg-green-50 text-green-900 mb-4 p-3">{message}</div>
  {/if}

  <!-- Email Allowlist -->
  <div class="mb-8">
    <h2 class="section-title">Email Allowlist</h2>
    <p class="text-xs text-ink-faint mb-3">Only these emails can sign in. Remove an email to revoke access.</p>

    <div class="flex gap-2 mb-4">
      <input
        class="input flex-1"
        type="email"
        placeholder="player@example.com"
        bind:value={newEmail}
        on:keydown={(e) => e.key === 'Enter' && addEmail()}
      />
      <button class="btn" on:click={addEmail} disabled={addingEmail}>
        {addingEmail ? 'Adding...' : 'Add'}
      </button>
    </div>

    {#if allowedEmails.length > 0}
      <div class="panel overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-ink/20">
              <th class="text-left py-2 px-3 font-semibold">Email</th>
              <th class="text-right py-2 px-3 font-semibold">Actions</th>
            </tr>
          </thead>
          <tbody>
            {#each allowedEmails as entry}
              <tr class="border-b border-ink/10 hover:bg-ink/5">
                <td class="py-2 px-3">{entry.email}</td>
                <td class="py-2 px-3 text-right">
                  <button
                    class="btn-danger text-xs"
                    on:click={() => removeEmail(entry)}
                  >
                    Remove
                  </button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {:else}
      <p class="text-ink-faint text-sm">No entries — all emails are currently allowed (open access).</p>
    {/if}
  </div>

  <!-- Database Backups -->
  <h2 class="section-title">Database Backups</h2>

  <div class="flex flex-wrap gap-3 mb-6">
    <button class="btn" on:click={createBackup} disabled={busy}>
      {busy ? 'Working...' : 'Create Backup'}
    </button>

    <div class="flex items-center gap-2">
      <input
        type="file"
        accept=".db"
        bind:this={fileInput}
        class="input text-sm"
      />
      <button class="btn" on:click={uploadRestore} disabled={busy}>
        Upload & Restore
      </button>
    </div>
  </div>

  {#if loading}
    <p class="text-ink/50">Loading backups...</p>
  {:else if backups.length === 0}
    <p class="text-ink/50">No backups yet. Create one to get started.</p>
  {:else}
    <div class="panel overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-ink/20">
            <th class="text-left py-2 px-3 font-semibold">Filename</th>
            <th class="text-left py-2 px-3 font-semibold">Size</th>
            <th class="text-left py-2 px-3 font-semibold">Created</th>
            <th class="text-right py-2 px-3 font-semibold">Actions</th>
          </tr>
        </thead>
        <tbody>
          {#each backups as backup}
            <tr class="border-b border-ink/10 hover:bg-ink/5">
              <td class="py-2 px-3 font-mono text-xs">{backup.filename}</td>
              <td class="py-2 px-3">{formatBytes(backup.size_bytes)}</td>
              <td class="py-2 px-3">{formatDate(backup.created_at)}</td>
              <td class="py-2 px-3 text-right">
                <div class="flex justify-end gap-2">
                  <button
                    class="btn-ghost text-xs"
                    on:click={() => downloadBackup(backup.filename)}
                  >
                    Download
                  </button>
                  <button
                    class="btn-ghost text-xs"
                    on:click={() => restoreBackup(backup.filename)}
                    disabled={busy}
                  >
                    Restore
                  </button>
                  <button
                    class="btn-danger text-xs"
                    on:click={() => deleteBackup(backup.filename)}
                    disabled={busy}
                  >
                    Delete
                  </button>
                </div>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</PageWrapper>
