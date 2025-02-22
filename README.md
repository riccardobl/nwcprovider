# NWC Service Provider Extension for [LNbits](https://github.com/lnbits/lnbits)

Easily connect your LNbits wallets via [NWC](https://nwc.dev/).

## Installation

Install the extension via the .env file or through the admin UI on your LNbits server. More details can be found [here](https://github.com/lnbits/lnbits/wiki/LNbits-Extensions).

## Configuration

Configure the extension from the "Settings" page in the top right menu when logged in as admin inside the extension page.

### Configuration Options:

| Key          | Description                                                                                                                                                                                                 | Default                         |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------- |
| relay        | URL of the nostr relay for dispatching and receiving NWC events. Use public relays or a custom one. Specify `nostrclient` to connect to the [nostrclient extension](https://github.com/lnbits/nostrclient). | nostrclient                     |
| provider_key | Nostr secret key of the NWC Service Provider.                                                                                                                                                               | Random key generated on install |
| relay_alias  | Relay URL to display in pairing URLs. Set if different from `relay`.                                                                                                                                        | Empty (uses the `relay` value)  |
| handle_missed_events | Number of seconds to look back for processing events missed while offline. Setting it to 0 disables this functionality. | 0 |


> [!WARNING]
>
> Do not change handle_missed_events from its default value of 0 unless you fully understand its implications. While a non-zero value may improve service quality under unstable conditions (e.g., poor connectivity or unreliable power), it can also lead to unexpected behavior. For example, in shared or community lnbits instances, where users are unaware of this functionality, they might assume a payment has failed and attempt to pay a new invoice with a different wallet, only for the instance to come back online and process the original payment request, potentially leading to duplicate payments. For this reason, unless you are trying to tackle this specific issue, it is recommended to leave this setting at 0.


### Using Nostrclient

The extension is preconfigured to connect to the nostrclient extension. Install it on the same LNbits instance and configure it to expose public websocket endpoints. Refer to the [nostrclient documentation](https://github.com/lnbits/nostrclient) for more information.

### Using a Custom Relay

To use a custom relay, set the `relay` key to the relay URL (e.g., `wss://nostr.wine`) in the extension's Settings page.

## Usage

1. Go to the extension page.
2. Select a wallet and click the plus button to create a new NWC connection.
3. Configure expiration, limits, and permissions.
4. A pairing URL will be generated for you to open, copy, or scan with the NWC app. Note that the pairing URL is shown only once, but you can delete and recreate the connection to get a new one.
