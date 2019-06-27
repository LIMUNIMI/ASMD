classdef AudioScoreDataset
    % A class to represent data, load them, split etc.
    properties
        data % the output of `jsondecode`: a structured array representing the dataset
        paths = [] % an cell-array containing the paths of the filtered songs
                    % [mixed paths, sources patshs, ground_truth paths]
        decompress_path
    end
    
    methods
        function obj = AudioScoreDataset(path)
            % Create a class instance by loading the json file specified in `path`
            obj.data = jsondecode(fileread('datasets.json'));
        end

        function filter(obj, varargin)
            % Filter the dataset according to the parameters:
            % - `instrument`:   a string representing the instrument that you
            %                   want to select (only one supported for now)
            % - `ensemble`:     if loading songs which are composed for an ensemble of
            %                   instrument (default `false`
            % - `mixed`:        if returning the mixed track for ensemble song
            %                   (default `true`)
            % - `sources`:      if returning the source track for ensemble recording
            %                   which provide it (default `false`)
            % - `all`:          only valid if `sources` is `true`: if `true`, all
            %                   sources (audio and ground-truth) are returned, if
            %                   `false`, only the target instrument is
            %                   returned. Default `false`.
            % - `composer`:     the surname of the composer to filter
            % - `ground_truth`: a list of strings representing the type of
            %                   ground-truths needed (logical AND among list elements)
            %
            % All parameters are optional and in name-value syntax

            % starting parser
            p = inputParser;
            addParameter(p, 'ensemble', false);
            addParameter(p, 'mixed', true);
            addParameter(p, 'sources', false);
            addParameter(p, 'all', false);
            addParameter(p, 'composer', -1);
            addParameter(p, 'instrument', -1);
            addParameter(p, 'ground_truth', -1);
            parse(p, varargin{:});

            for i = 1:length(obj.data.datasets)
                FLAG = true;

                % checking dataset-level filters
                if p.Results.ensemble ~= dataset.ensemble
                    FLAG = false;
                end

                if p.Results.instrument ~= -1
                    if ~contains(dataset.instruments, p.Results.instrument)
                        FLAG = false;
                    end
                end

                if p.Results.sources
                    if dataset.sources.format ~= 'unknown'
                        FLAG = false;
                    end
                end

                if p.Results.ground_truth ~= -1
                    for gt = p.Results.ground_truth
                        if ~getfield(dataset.ground_truth, gt)
                            FLAG = false;
                            break;
                        end
                    end
                end

                if FLAG
                    disp(dataset.name);
                    for k = 1:length(dataset.songs)
                        song = dataset.songs(k);
                        % checking song levels filters
                        if p.Results.instrument ~= -1
                            if ~contains(song.instruments, p.Results.instrument)
                                FLAG = false;
                            end
                        end

                        if p.Results.composer ~= -1
                            if ~strcmp(p.Results.composer, song.composer)
                                FLAG = false;
                            end
                        end

                        if FLAG
                            gts = {song.ground_truth};
                            sources = {};
                            mixed = {};
                            if p.Results.sources
                                if p.Results.all
                                    sources = {song.sources.path};
                                else
                                    % find the index of the instrument
                                    idx = find(contains(song.instruments, p.Results.instrument));

                                    % take index of the target instrument
                                    sources = {song.sources.path(idx)};
                                    gts = {song.ground_truth(idx)};
                                end
                            end

                            if p.Results.mixed
                                mixed = {song.recording.path};
                            end
                            paths = [paths; mixed sources gts];
                        end % closing `if FLAG` check

                    end % closing song loop
                end % closing `if FLAG` check
            end % closing dataset loop
        end % closing method

        function move_to_ram(obj, tmpfs)
            % - `tmpfs`: a string representing the directory where the returned
            %            ground truth files are copied. In linux, it is
            %            recommended to use a tmpfs filesystem.  If free space
            %            is enough, than all ground-truth files are
            %            moved there, so that every compressed file is already
            %            in RAM. Also, every file will be decompressed in this
            %            path.
            %
            %            I recommend to do not use this parameter if not in
            %            linux.
            %
            %            Note that all the ground-truth files need at least XX
            %            GB of RAM, but if you filter them, you'll need less
            %            space.
            for i = 1:length(obj.paths)
                for j = 1:length(obj.paths{i, 3})
                    filepath = obj.paths{i, 3}{j};
                    if ~movefile(filepath, tmpfs)
                        fprintf('Cannot move %s\n', filepath);
                        return;
                    end
                end
            end

            obj.set_decompress_path(tmpfs)
        end

        function set_decompress_path(obj, tmpfs)
            % - `tmpfs`: a string representing the directory where the returned
            %            ground truth files are decompressed. In linux, it is
            %            Needed at least XX MB or free space.
            %
            %            I recommend to do not use this parameter if not in
            %            linux.
            obj.decompress_path = tmpfs;
        end

        function mix sources gts = get_item(obj, idx)
            % - `idx`: the index of the wanted item.
            %
            % RETURNED:
            % - `mix`:      the audio waveform of the mixed song (array)
            % - `sources`:  the audio values of each sources (nx1 cell-array)
            % - `gts`:      the ground-truths of each source (or of the mixed track
            %               if sources is empty) (nx1 cell-array)
            %
        end

    end % closing method section
end % closing class
