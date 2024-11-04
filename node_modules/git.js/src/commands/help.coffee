_ = require 'underscore'

# help command plugin
module.exports = (git) ->
	return (cmd, opts) ->
		args = [transform(opts)..., cmd]
		git.run('help', args)

transform = (opts) ->
	return [] unless opts
	_.keys(opts)
	.map (k) ->
			v = opts[k]
			switch k
				when 'all' then "--all"
				when 'info' then "--info"
				when 'man' then "--man"
				when 'web' then "--web"
				when 'format'
					switch v
						when 'info' then "--info"
						when 'man' then "--man"
						when 'web' then "--web"
						else ''
				else ''
	.filter _.identity
