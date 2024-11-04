_ = require 'underscore'

# init command plugin
module.exports = (git) ->
	return (opts) ->
		args = ['--quiet', transform(opts)...]
		git.run('init', args)

transform = (opts) ->
	return [] unless opts
	# todo support more options
	_.keys(opts)
	.map (k) ->
			v = opts[k]
			switch k
				when 'bare' then "--bare"
				when 'shared' then "--shared=#{v}"
				else ''
	.filter _.identity
