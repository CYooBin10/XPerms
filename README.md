<div align="center">
  <img src="icon.png" alt="XPerms Icon" width="150" height="150">
  <h2>XPerms</h2>
  <p>Plugin manages player permissions (Rank/Permission) and prefixes (Suffixes) on the Minecraft Bedrock Edition (Endstone) server.</p>
</div>

[![Downloads](https://endgit.dev/shield.dl.total/xperms)](https://endgit.dev/plugins/xperms) [![Status](https://endgit.dev/shield.state/xperms)](https://endgit.dev/plugins/xperms) [![API](https://endgit.dev/shield.api/xperms)](https://endgit.dev/plugins/xperms)

# XPerms

XPerms is permission, group, prefix, suffix, and chat-format plugin for Endstone Bedrock servers. Version 2 uses schema v2 storage, deterministic permission resolution, multi-group membership, inheritance, contexts, and temporary permission nodes.

## Install

1. Install `endstone-xperms` in server plugins directory.
2. Start server. XPerms creates `plugins/XPerms/data.json`.
3. Grant `xperms.admin` to manage XPerms. It defaults to OP.

`jwplaceholderapi` is optional. When installed, XPerms registers its placeholder expansion.

## Storage and schema v2

Data lives in `plugins/XPerms/data.json`. Schema v2 stores `schema_version`, `default_group`, identity maps, groups, and users. Permission entries are node objects with fields such as `permission`, `value`, optional `context`, and optional `expires_at`.

On load, XPerms accepts legacy unversioned/schema v1 data and migrates valid data to v2 on next save. Invalid groups or users are skipped or normalized; missing groups and invalid memberships fall back to valid defaults.

Writes use temporary file replacement. Before replacing existing `data.json`, XPerms copies it to `data.json.bak`. On load failure, it tries `data.json.bak`; failed reload keeps active data.

## Commands

All commands start with `/xperms`.

### Existing commands

| Command | Action |
|---|---|
| `groups` | List groups |
| `create <name>` | Create group |
| `delete <name>` | Delete non-default group; affected users move to default group |
| `info <name>` | Show group prefix, suffix, permissions |
| `setprefix <name> <prefix>` | Set prefix |
| `setsuffix <name> <suffix>` | Set suffix |
| `setformat <name> <format>` | Set chat format |
| `addperm <name> <permission>` | Add allow permission node |
| `removeperm <name> <permission>` | Remove permission node |
| `setgroup <player> <group>` | Replace player membership with group |
| `playerinfo <player>` | Show primary group, prefix, suffix |
| `reload` | Reload storage and refresh online players |
| `default` | Show default group |
| `setdefault <group>` | Set default group |

### v2 commands

| Command | Action |
|---|---|
| `user <player> permission set <node> [true/false]` | Set direct boolean user node |
| `user <player> permission unset <node>` | Remove direct user node |
| `user <player> permission check <node>` | Check resolved node for user |
| `user <player> group add <group>` | Add membership |
| `user <player> group remove <group>` | Remove membership when another remains |
| `user <player> group primary <group>` | Set primary group from membership |
| `group <group> parent add <parent>` | Add inherited parent; cycles rejected |
| `group <group> parent remove <parent>` | Remove inherited parent |
| `explain <player> <node>` | Show selected resolver result and candidates |

## Permission resolution

Resolver returns `false` when no matching node exists. It evaluates direct user nodes, then user groups and inherited parents. Matching rules are deterministic:

1. Direct user nodes beat group nodes.
2. Exact permissions beat wildcards.
3. More context keys beat fewer.
4. Higher node priority, higher group weight, then lower inheritance depth win.
5. Remaining ties sort by permission name.

Both `true` and `false` nodes are supported. Wildcards end in `.*`: `build.*` matches `build` and `build.place`. A node applies only when every node context matches current player context.

Live player contexts: `server=default`, `level`, `dimension`, `game_mode`, `device_os`, and `xuid_present`. Permission attachments refresh on join, game-mode change, dimension change, group changes, and relevant permission changes.

## Temporary nodes and core API

`PermissionNode` supports `expires_at`; expired nodes do not resolve. `Storage.cleanup_expired()` removes expired nodes. Plugin runs cleanup every 1,200 ticks.

Core classes: `PermissionNode`, `User`, `Group`, `Track`, `Resolver`, `Resolution`, and `Storage`. `parse_duration()` accepts seconds or `[Nd][Nh][Nm][Ns]`; `expiration()` converts duration to timestamp. These helpers exist for API use; current command syntax does not create temporary nodes, contexts, priorities, or weights.

## Placeholders

With `jwplaceholderapi`, expansion identifier is `xperm`.

| Placeholder | Value |
|---|---|
| `%xperm_group%`, `%xperm_primary_group%` | Primary group |
| `%xperm_all_groups%` | Comma-separated memberships |
| `%xperm_prefix%`, `%xperm_suffix%` | Primary group display values |
| `%xperm_permission%` | Effective permission map |
| `%xperm_permission_<node>%` | `true` or `false` for node |
| `%xperm_context%` | Current context map |

## Chat format

Group chat format supports `{prefix}`, `{name}`, `{suffix}`, and `{message}`. Default: `{prefix} {name}{suffix}§r: {message}`.

## Performance and recovery

Resolver results cache by user, node, context, time argument, and resolver revision. Plugin rebuilds resolver when storage revision changes. Permission attachments are replaced on refresh, then player permissions recalculate. Storage only writes when dirty and batches command writes for 20 ticks.

## Limitations

No Form UI. No audit log or rollback. No tracks or meta management UI. No database backend. No command interface for contexts, temporary durations, node priority, or group weight.
