require 'should'
fs = require 'fs'
path = require 'path'
tmp = path.join __dirname, 'tmp'

create = ->
	fs.mkdirSync tmp unless fs.existsSync tmp
	require('../index')(tmp)

clean = ->
	fs.rmdirSync tmp

git = null

describe 'git object', ->
	describe 'created for temp dir', ->

		beforeEach ->
			git = create()

		afterEach ->
			clean()

		it 'should expose the following commands', ->
			[
				'add', 'remove', 'rm',
				'commit', 'config',
				'diff', 'init', 'log',
				'pull', 'push',
				'status', 'show',
				'revert', 'tag', 'help'
			].forEach (cmd) ->
				git.should.have.property(cmd)
				git[cmd].should.be.instanceof(Function)
				(typeof git[cmd]).should.be.eql 'function'
