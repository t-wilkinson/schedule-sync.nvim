local job = require("plenary.job")

vim.api.nvim_create_user_command("SyncSchedule", function()
	local current_buffer_filename = vim.fn.expand("%:p")
	local venv_activate_cmd = "source " .. vim.fn.getcwd() .. "/.venv/bin/activate"
	job:new({
		command = "bash",
		args = {
			"-c",
			venv_activate_cmd .. " && python3 -m calendar_sync.sync_schedule " .. current_buffer_filename,
		},
		on_exit = function(j, return_code)
			if return_code == 0 then
				print("Schedule synced successfully!")
			else
				print("Error syncing schedule. Check your_script.py for details.")
			end
		end,
	}):start()
end, {})
