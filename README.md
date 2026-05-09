<div align="center">
  <img src="icon.png" alt="XPerms Icon" width="150" height="150">
  <h2>XPerms</h2>
  <p>Plugin manages player permissions (Rank/Permission) and prefixes (Suffixes) on the Minecraft Bedrock Edition (Endstone) server.</p>
</div>

## Overview

XPerms is a lightweight, easy-to-use permission management plugin for Endstone servers. It allows you to create groups, assign permissions, and customize player prefixes and suffixes for an enhanced server experience.

Inspired by **LuckPerms** but designed with **simplicity and lightweight** in mind.

## Features

- ✅ Create and manage player groups/ranks
- ✅ Assign permissions to groups
- ✅ Customize player prefixes and suffixes
- ✅ Chat format customization with color code support
- ✅ Simple JSON-based data storage
- ✅ Hot-reload support (no server restart needed)

## Configuration

The plugin uses JSON for data storage. Configuration files are automatically generated on first run.

### Default Files

- `plugins/XPerms/data.json` - Stores groups and player data
- `plugins/XPerms/config.toml` - Server configuration

### Data Structure (data.json)

```json
{
  "default_group": "default",
  "groups": {
    "default": {
      "prefix": "§7[Member]",
      "suffix": "",
      "permissions": [],
      "chat_format": "{prefix} {name}{suffix}§r: {message}"
    },
    "vip": {
      "prefix": "§a[VIP]",
      "suffix": "",
      "permissions": ["vip.extra"],
      "chat_format": "{prefix} {name}{suffix}§r: {message}"
    }
  },
  "users": {
    "playername": {
      "group": "vip"
    }
  }
}
```

## Commands

All commands use the `/xperms` prefix and require the `xperms.admin` permission (OP by default).

### Group Management Commands

| Command | Description |
|---------|-------------|
| `/xperms groups` | List all groups |
| `/xperms create <name>` | Create a new group |
| `/xperms delete <name>` | Delete a group (moves users to default) |
| `/xperms info <name>` | View group information |
| `/xperms setprefix <name> <prefix>` | Set group prefix (supports §color codes) |
| `/xperms setsuffix <name> <suffix>` | Set group suffix |
| `/xperms setformat <name> <format>` | Set custom chat format |
| `/xperms addperm <name> <permission>` | Add permission to group |
| `/xperms removeperm <name> <permission>` | Remove permission from group |

### Player Management Commands

| Command | Description |
|---------|-------------|
| `/xperms setgroup <player> <group>` | Assign a group to player |
| `/xperms playerinfo <player>` | View player information |

### System Commands

| Command | Description |
|---------|-------------|
| `/xperms reload` | Reload plugin data and configuration |

## Examples

### Create Groups with Prefixes

```
/xperms create vip
/xperms setprefix vip §a[VIP]

/xperms create admin
/xperms setprefix admin §c[Admin]
```

### Add Permissions

```
/xperms addperm vip vip.extra
/xperms addperm admin xperms.admin
/xperms addperm admin admin.build
```

### Assign Players to Groups

```
/xperms setgroup PlayerName vip
/xperms setgroup AdminName admin
```

### View Information

```
/xperms groups
/xperms info vip
/xperms playerinfo PlayerName
```

## Chat Format

The plugin supports custom chat formats with the following placeholders:

- `{prefix}` - Player's group prefix
- `{name}` - Player's name
- `{suffix}` - Player's group suffix
- `{message}` - The chat message

**Default format:** `{prefix} {name}{suffix}§r: {message}`

**Example custom format:** `§7[§r{prefix}§7]§r {name}§r: §f{message}`
