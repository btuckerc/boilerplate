return {
  "tris203/precognition.nvim",
  event = "VeryLazy",
  opts = {
    startVisible = false,
  },
  keys = {
    {
      "<leader>pp",
      function()
        require("precognition").toggle()
      end,
      desc = "Toggle Precognition",
    },
  },
  config = function(_, opts)
    require("precognition").setup(opts)
  end,
}
