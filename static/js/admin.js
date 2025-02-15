window.app = Vue.createApp({
    el: "#vue",
    mixins: [windowMixin],
    delimiters: ["${", "}"],
    data: function () {
      return {
        entries: [],
        columns: [
          {
            name: "key",
            required: true,
            label: "Key",
            align: "left",
            field: (row) => row.key,
            sortable: true,
          },
          {
            name: "value",
            required: true,
            label: "Value",
            align: "left",
            field: (row) => row.value,
            sortable: true,
          },
        ],
      };
    },

    methods: {
      fetchConfig() {
        this.entries = [];
        LNbits.api
          .request(
            "GET",
            "/nwcprovider/api/v1/config",
            this.g.user.wallets[0].adminkey,
          )
          .then((response) => {
            const newEntries = [];
            for (const [key, value] of Object.entries(response.data)) {
              newEntries.push({
                key: key,
                value: value,
              });
            }

            this.entries = newEntries;
          })
          .catch(function (error) {
            console.error("Error fetching config:", error);
          });
      },
      async saveConfig() {
        const data = {};
        for (const entry of this.entries) {
          data[entry.key] = entry.value;
        }
        try {
          const response = await LNbits.api.request(
            "POST",
            "/nwcprovider/api/v1/config",
            this.g.user.wallets[0].adminkey,
            data,
          );
          this.$q.notify({
            message: "Config saved, please restart the server",
            color: "positive",
            position: "top",
            timeout: 2000,
            actions: [{ icon: "close", color: "white" }],
          });
        } catch (error) {
          console.error("Error saving config:", error);
        }
      },
    },

    created: function () {
      this.fetchConfig();
    },
  });