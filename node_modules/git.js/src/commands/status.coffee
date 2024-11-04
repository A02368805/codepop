_ = require 'underscore'
parse = require '../../parse/status'

# status command plugin
module.exports = (git) ->
	return (opts) ->
		opts = {} unless opts
		args = if opts.full then [] else ['-s']
		git.run('status', args).then(parseFn(opts))

# selects parser
parseFn = (opts) ->
	return parse.full if opts.full
	return parse.short
