_ = require 'underscore'
parse = require 'parse-diff'
Q = require 'q'
diff_opts = require '../../opts/diff'

# diff command plugin
module.exports = (git) ->
	cmd = (commits, opts) ->
		# be smart, by default show changes
		if not commits || commits.length == 0
			return cmd.files([], opts)
		if commits.length > 2
			return Q.reject 'diff failed: bad number of commits'
		# using unified diff format
		args = ['-u', diff_opts(opts)...]
		git.run('diff', [args..., commits...]).then(parse)
	# diff files
	cmd.files = (files, opts) ->
		# todo support more options
		files = [] unless files
		# using unified diff format
		args = ['-u', diff_opts(opts)...]
		git.run('diff-files', [args..., files...]).then(parse)
	cmd
