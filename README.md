# tvdinner.jellyfin

Manage Jellyfin API keys, libraries and items. Part of the [tvdinner](https://gitea.stump.rocks/tvdinner)
collection family; HTTP handling comes from `tvdinner.core`'s shared REST
client.

## Install

`tvdinner.core` is a dependency and is not published to Galaxy, so install both
from git via a `requirements.yml`:

```yaml
collections:
  - name: https://gitea.stump.rocks/tvdinner/ansible-collection-core.git
    type: git
    version: main
  - name: https://gitea.stump.rocks/tvdinner/ansible-collection-jellyfin.git
    type: git
    version: main
```

```sh
ansible-galaxy collection install -r requirements.yml
```

## Development

```sh
git clone https://gitea.stump.rocks/tvdinner/ansible-collection-core.git ../tvdinner-core
make check   # lint + test
```

## License

MIT
