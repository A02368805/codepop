_ = require 'underscore'
_.str = require 'underscore.string'

# commit command plugin
module.exports = (git) ->
	return (opts) ->
		files = opts.files || []
		args = [transform(opts)..., files...]
		git.run('commit', args)

transform = (opts) ->
	return [] unless opts
	# todo support more options
	_.keys(opts)
	.map (k) ->
			v = opts[k]
			switch k
				# do not create a commit, but show a list of paths that are to be committed.
				when 'dryrun' then "--dry-run"
				when 'all' then "-a"
				when 'message' then "-m #{_.str.quote(v, '\'')}"
				else ''
	.filter _.identity
