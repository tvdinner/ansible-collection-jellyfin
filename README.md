# tvdinner.jellyfin

Manage Jellyfin API keys, libraries and items. Part of the [tvdinner](https://gitea.stump.rocks/tvdinner)
collection family; HTTP handling comes from `tvdinner.core`'s shared REST
client.

## Install

```sh
ansible-galaxy collection install git+https://gitea.stump.rocks/tvdinner/ansible-collection-jellyfin.git
```

Requires `tvdinner.core`.

## Development

```sh
git clone https://gitea.stump.rocks/tvdinner/ansible-collection-core.git ../tvdinner-core
make check   # lint + test
```

## License

MIT
