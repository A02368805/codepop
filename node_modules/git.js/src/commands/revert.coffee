_ = require 'underscore'

# revert command plugin
module.exports = (git) ->
	return (commits, opts) ->
		args = [transform(opts)..., commits...]
		git.run('revert', args)

transform = (opts) ->
	return [] unless opts
	# todo support more options
	_.keys(opts)
	.map (k) ->
			v = opts[k]
			switch k
				when 'strategy' then "--strategy=#{v}"
				when 'nocommit' then "--no-commit"
				when 'no-commit' then "--no-commit"
				else ''
	.filter _.identity
