_ = require 'underscore'
parse = require 'parse-diff'
diff_opts = require '../../opts/diff'

# show command plugin
module.exports = (git) ->
	show = (obj, opts) ->
		args = [show_opts(opts)..., obj]
		git.run('show', args)
	show.diff = (commit, opts) ->
		args = ['-u', '--format=format:%b', diff_opts(opts)..., commit]
		git.run('show', args).then(parse)
	show

show_opts = (opts) ->
	return [] unless opts
	# todo support more options
	_.keys(opts)
	.map (k) ->
			v = opts[k]
			switch k
				when 'format' then "--format=#{{v}}"
				else ''
	.filter _.identity
