# Using BigQuery with vim-dadbod

This document outlines how to use `vim-dadbod` to connect to Google BigQuery.

## Prerequisites

The `vim-dadbod` BigQuery adapter uses the `gcloud` command-line tool (`bq`) to interact with BigQuery. Before you can connect, you must:

1.  **Install the Google Cloud SDK.**
    Follow the official instructions: [https://cloud.google.com/sdk/docs/install](https://cloud.google.com/sdk/docs/install)

2.  **Authenticate with Google Cloud.**
    Run the following command and follow the instructions to log in to your Google account:
    ```sh
    gcloud auth application-default login
    ```

3.  **Set your default project.**
    You need to configure your default Google Cloud project. This project will be used by `vim-dadbod` if you don't specify one in the connection URL.
    ```sh
    gcloud config set project YOUR_PROJECT_ID
    ```
    Replace `YOUR_PROJECT_ID` with your actual BigQuery project ID.

## Connection

`vim-dadbod` connects to BigQuery using a URL.

### Connection URL

The URL format for BigQuery is:

```
bigquery://[PROJECT_ID]
```

*   If you have a default project set with `gcloud`, you can omit the project ID:
    ```
    bigquery://
    ```
    or simply
    ```
    bigquery:
    ```

*   To connect to a specific project, use:
    ```
    bigquery://YOUR_PROJECT_ID
    ```

## Usage

You can use the `:DB` command to execute queries.

### Interactive Console

To open an interactive `bq` shell:

```vim
:DB bigquery://
```

### Running Queries

To run a query on the current buffer:

```vim
:%DB bigquery://YOUR_PROJECT_ID
```

Or, if you have a default project configured:

```vim
:%DB bigquery://
```

For example, create a file `my_query.sql` with the following content:

```sql
SELECT
  name,
  SUM(number) AS total
FROM
  `bigquery-public-data.usa_names.usa_1910_2013`
WHERE
  name = 'William'
GROUP BY
  name;
```

Then run it with:

```vim
:%DB bigquery://bigquery-public-data
```

### Using with vim-dadbod-ui

With `vim-dadbod-ui`, you can add your BigQuery connection to the UI.

You can add the following to your Neovim configuration to have the connection show up in the DBUI list:

```lua
-- In your vim-dadbod-ui configuration
vim.g.dbs = {
  { name = 'My BQ Project', url = 'bigquery://YOUR_PROJECT_ID' }
}
```

Replace `YOUR_PROJECT_ID` with your project ID. You can add multiple projects to the list.
